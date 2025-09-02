from datetime import timezone, datetime, timedelta
import os
import shutil
import uuid

import pandas.errors
from services.ModelTrainer import ModelTrainer
from services.PrintGraph import PrintGraph
from database import SessionLocal, get_db
from dependencies import get_current_user
from fastapi import UploadFile, File
from models.file_model import UserFile

from fastapi.params import Depends
from fastapi.responses import JSONResponse
import pandas as pd
import io
from services.DataPreprocessor import DataPreprocessor
from fastapi import APIRouter
from models.temp_file_model import TempFile
from models.user_model import User
from schemas.file_schema import ReturnFile
from schemas.user_schama import TargetColumnRequest

import tempfile
from fastapi import BackgroundTasks
import base64

from services.send_action import send_action
from starlette.responses import FileResponse

router = APIRouter()
@router.post("/upload-csv/show_column")
async def upload_csv(file: UploadFile = File(...),
                     user: User = Depends(get_current_user),
                     db: SessionLocal = Depends(get_db)):
    if file.content_type != "text/csv":
        return JSONResponse(status_code=400, content={"error": "The file must be in CSV format."})

    try:
        data = await file.read()
        data_decoded = data.decode('utf-8')
        pd_data = pd.read_csv(io.StringIO(data_decoded))
    except pandas.errors.EmptyDataError:
        return JSONResponse(status_code=400, content={"error": "Uploaded file is empty"})
    except pd.errors.ParserError:
        return JSONResponse(status_code=400, content={"error": "Uploaded file is not a valid CSV"})
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Not Found error"})

    unique_filename = f"{user.id}_{uuid.uuid4().hex}_{file.filename}"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp_file:
        tmp_file.write(data_decoded)
        tmp_path = tmp_file.name

    temp_file = TempFile(
        user_id = user.id,
        tmp_path = tmp_path,
        original_filename = unique_filename
    )
    db.add(temp_file)
    db.commit()
    db.refresh(temp_file)

    try:
        data_prepare = DataPreprocessor(pd_data)
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error": str(error)})
    return JSONResponse(content={"columns": data_prepare.show_file_columns(), "file_id": temp_file.id})



@router.post("/upload-csv/set_target_column")
async def set_target_column(request: TargetColumnRequest,
                            background_tasks: BackgroundTasks,
                            user: User = Depends(get_current_user),
                            db: SessionLocal = Depends(get_db)
):
    file = db.query(TempFile).filter(TempFile.user_id == user.id, TempFile.id == request.file_id).first()
    if not file:
        return JSONResponse(status_code=404, content={"error": "Uploaded CSV not found"})


    try:
        send_action(user_id=user.id,action_type="generate decision tree")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    tmp_path = file.tmp_path
    original_filename = file.original_filename

    try:
        pd_data = pd.read_csv(tmp_path)
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to read temporary file"})

    if request.target_column not in pd_data.columns:
        return JSONResponse(status_code=400, content={"error": "Selected column not found in dataset"})

    data_prepare = DataPreprocessor(pd_data)

    try:
        X, y, final_data = data_prepare.prepare_data(request.target_column)
    except pd.errors.ParserError:
        return JSONResponse(status_code=400, content={"error": "Invalid CSV format."})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    print("Wybrane cechy:", list(X))
    analyze_data = ModelTrainer(X, y, checked=request.type_search)
    full_metrics = analyze_data.train_model()

    selected_columns = analyze_data.find_best_attributes()
    print("Wybrane cechy:", list(selected_columns))
    selected_metrics = analyze_data.train_model(selected_columns)

    graph = PrintGraph(
        analyze_data.model,
        feature_names=analyze_data.used_features,
        class_names=data_prepare.label_encoder.inverse_transform(range(len(data_prepare.label_encoder.classes_))),
        all_feature_names=final_data.drop(columns=request.target_column).columns
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "tree")
        graph.save(output_path, format_file="png")

        final_path = output_path + ".png"
        if not os.path.exists(final_path):
            return JSONResponse(status_code=500, content={"error": "Graph image not created"})

        with open(final_path, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    if request.save_file:
        storage_dir = os.path.join("storage", str(user.id))
        os.makedirs(storage_dir, exist_ok=True)
        dest_path = os.path.join(storage_dir, original_filename)

        shutil.move(tmp_path, dest_path)

        new_file = UserFile(
            user_id=user.id,
            filename=original_filename,
            storage_path=os.path.join(f"{user.id}", original_filename),
            size_bytes=os.path.getsize(dest_path),
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(new_file)
        db.delete(file)
        db.commit()
        db.close()
    else:
        def cleanup_files():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                db.delete(file)
                db.commit()
            except Exception as error:
                print(f"Error cleaning up files: {error}")
        background_tasks.add_task(cleanup_files)

    return JSONResponse(content={
        "image_base64": img_b64,
        "full_model_metrics": {k: f"{v:.3f}" for k, v in full_metrics.items()},
        "selected_columns_metrics": {k: f"{v:.3f}" for k, v in selected_metrics.items()},
        "best_columns_sorted": analyze_data.sort_best_column()
    })

@router.get("/get_file/files", response_model=list[ReturnFile])
def return_files(
    user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    files = db.query(UserFile).filter(UserFile.user_id == user.id).all()
    return [ReturnFile.model_validate(file) for file in files]

@router.get("/get_file/file/download/{file_id}")
def download_user_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == user.id
    ).first()

    if not file:
        return JSONResponse(content={"error": "Access denied or File not found"})

    print(f"user.id={user.id}, file_id={file_id}")
    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == user.id
    ).first()
    print(f"file from DB: {file}")

    return FileResponse(
        path=os.path.join("storage", file.storage_path),
        filename=ReturnFile.model_validate(file).filename,
        media_type="application/octet-stream"
    )