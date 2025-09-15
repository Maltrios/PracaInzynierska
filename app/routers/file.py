from datetime import timezone, datetime, timedelta
import os
import shutil
import uuid

from celery.bin.control import status

import pandas.errors
from services.ModelTrainer import ModelTrainer
from services.PrintGraph import PrintGraph
from database import SessionLocal, get_db
from dependencies import get_current_user
from fastapi import UploadFile, File, status
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
from celery_app.tasks import analyse_data
import tempfile
from fastapi import BackgroundTasks
import base64

from services.send_action import send_action
from starlette.responses import FileResponse

router = APIRouter()
@router.post("/upload-csv/show_column",
             summary="Insert csv file to select decision column",
             description="""
                            Upload a CSV file to validate it and return the names of available columns.
                          """,
             responses={
                 400: {"description": "Error during file validation",
                       "content": {
                           "application/json": {
                               "examples": {
                                   "empty_file": {"value": {"detail": "Uploaded file is empty"}},
                                   "not_csv_file": {"value": {"detail": "Uploaded file is not a valid CSV"}},
                                   "unspecified_error": {"value": {"detail": "Not Found error"}},
                                   "bad_format": {"value": {"detail": "The file must be in CSV format."}},
                               }
                           }
                       }
                       },
                 413: {"description": "Upload file is too large"},
                 200: {"description": "Upload and validate file successfully",
                       "content":{
                            "application/json": {
                                "example": {
                                    "columns": ["name1", "name2", "name3"],
                                    "file_id": 4
                                }
                            }
                       }
                       }

             })
async def upload_csv(file: UploadFile = File(...),
                     user: User = Depends(get_current_user),
                     db: SessionLocal = Depends(get_db)):
    if file.content_type != "text/csv":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "The file must be in CSV format."})

    try:
        data = await file.read()

        if len(data) > int(os.getenv("MAX_UPLOAD_SIZE")):
            return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                content={"detail": "File too large"})

        data_decoded = data.decode('utf-8')
        pd_data = pd.read_csv(io.StringIO(data_decoded))
    except pandas.errors.EmptyDataError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Uploaded file is empty"})
    except pd.errors.ParserError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Uploaded file is not a valid CSV"})
    except Exception:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Not Found error"})

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
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(error)})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"columns": data_prepare.show_file_columns(), "file_id": temp_file.id})


@router.post("/start-analysis", summary="add the decision tree generation task to the queue",
             description="""
                           
                          """,
             responses={
                 404: {"description": "Uploaded CSV not found"},
                 500: {"description": "internal microservice error"},
                 200: {"description": "the user's task ID was returned"}
             })
def start_analysis(request: TargetColumnRequest,
                            user: User = Depends(get_current_user),
                            db: SessionLocal = Depends(get_db)):

    file = db.query(TempFile).filter(TempFile.user_id == user.id, TempFile.id == request.file_id).first()

    if not file:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Uploaded CSV not found"})

    try:
        send_action(user_id=user.id,action_type="generate decision tree")
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})

    tmp_path = file.tmp_path
    original_filename = file.original_filename

    task = analyse_data.delay(file.id, tmp_path, request.target_column, request.save_file, user.id,original_filename, request.type_search)
    return {"task_id": task.id}


@router.get("/get_file/files", response_model=list[ReturnFile],
            summary="Displays user files stored in memory",
            description="""
                            All files saved by a given user will be displayed
                        """,
            responses={
                401: {"description": "Not authenticated"},
                400: {"description": "Access denied or File not found"},
                200: {"description": "File name display completed successfully"}
            })
def return_files(
    user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    files = db.query(UserFile).filter(UserFile.user_id == user.id).all()
    return [ReturnFile.model_validate(file) for file in files]

@router.get("/get_file/file/download/{file_id}",
            summary="Downloading a file with the provided ID",
            description="""
                          Enabling the download of a file submitted by the user to the database.
                          The response will be the file content as a binary stream with appropriate filename.
                        """,
            responses={
                401: {"description": "Not authenticated"},
                404: {"description": "Access denied or File not found"},
                200: {"description": "User successfully downloaded file",
                      "content": {
                           "application/octet-stream": {
                               "example": {
                                    "example": "Binary content placeholder"
                               }
                           }
                      }
                      }
            })
def download_user_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Not authenticated"})

    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == user.id
    ).first()

    if not file:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Access denied or File not found"})

    print(f"user.id={user.id}, file_id={file_id}")
    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == user.id
    ).first()
    print(f"file from DB: {file}")

    return FileResponse(
        path=os.path.join(os.getenv("STORAGE_DIR"), file.storage_path),
        filename=ReturnFile.model_validate(file).filename,
        media_type="application/octet-stream"
    )

