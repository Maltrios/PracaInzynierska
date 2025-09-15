import base64
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from time import sleep

from celery_app.config import celery_app, r

import pandas as pd
from database import SessionLocal
from matplotlib.pyplot import close
from models.file_model import UserFile
from models.temp_file_model import TempFile
from services.DataPreprocessor import DataPreprocessor
from services.ModelTrainer import ModelTrainer
from services.PrintGraph import PrintGraph
from services.send_action import send_action

@celery_app.task(bind=True)
def analyse_data(self,file_id: int, tmp_path: str, target_column: str, save_file: bool, user_id: int,original_filename: str, type_search: bool, db=None):
    # sleep(10)
    r.set(f"task:{self.request.id}:progress",
          json.dumps({'progress': 0, 'detail': 'starting'}))

    if db is None:
        db = SessionLocal()
    try:
        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 5, 'detail': 'read csv file'}))
        try:
            pd_data = pd.read_csv(tmp_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV file: {str(e)}")

        if target_column not in pd_data.columns:
            raise ValueError("Selected column not found in dataset")

        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 10, 'detail': 'data pre-processing'}))
        data_prepare = DataPreprocessor(pd_data)


        try:
            X, y, final_data = data_prepare.prepare_data(target_column)
        except pd.errors.ParserError:
            raise Exception("Invalid CSV format.")
        except ValueError as e:
            raise ValueError(f"{str(e)}")

        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 20, 'detail': 'Training model'}))

        analyze_data = ModelTrainer(X, y, checked=type_search)
        full_metrics = analyze_data.train_model()

        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 40, 'detail': 'Evaluating selected columns'}))

        selected_columns = analyze_data.find_best_attributes()
        selected_metrics = analyze_data.train_model(selected_columns)

        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 70, 'detail': 'Generating graph'}))

        graph = PrintGraph(
            analyze_data.model,
            feature_names=analyze_data.used_features,
            class_names=data_prepare.label_encoder.inverse_transform(range(len(data_prepare.label_encoder.classes_))),
            all_feature_names=final_data.drop(columns=target_column).columns
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "tree")
            graph.save(output_path, format_file="png")

            final_path = output_path + ".png"
            if not os.path.exists(final_path):
                raise ValueError("Graph image not created")

            with open(final_path, "rb") as f:
                img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")


        if save_file:
            r.set(f"task:{self.request.id}:progress",
                  json.dumps({'progress': 90, 'detail': 'Save file to database'}))

            storage_dir = os.path.join(os.getenv("STORAGE_DIR"), str(user_id))
            os.makedirs(storage_dir, exist_ok=True)
            dest_path = os.path.join(storage_dir, original_filename)

            shutil.move(tmp_path, dest_path)

            new_file = UserFile(
                user_id=user_id,
                filename=original_filename,
                storage_path=os.path.join(f"{user_id}", original_filename),
                size_bytes=os.path.getsize(dest_path),
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            )
            db.add(new_file)
            db.commit()
        else:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        result = {
                "image_base64": img_b64,
                "full_model_metrics": {k: f"{v:.3f}" for k, v in full_metrics.items()},
                "selected_columns_metrics": {k: f"{v:.3f}" for k, v in selected_metrics.items()},
                "best_columns_sorted": analyze_data.sort_best_column()
            }

        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': 100, 'detail': 'Analysis complete', "result": result}))
        return result
    except Exception as e:
        r.set(f"task:{self.request.id}:progress",
              json.dumps({'progress': -1, 'detail': str(e), 'status': 'failed'}))
        raise
    finally:
        try:
            file = db.query(TempFile).filter(TempFile.id == file_id).first()
            if file:
                try:
                    if getattr(file, "tmp_path", None) and os.path.exists(file.tmp_path):
                        os.remove(file.tmp_path)
                except Exception as cleanup_error:
                    r.set(f"task:{self.request.id}:progress",
                          json.dumps({'progress': -1, 'detail': f'Cleanup error: {cleanup_error}', 'status': 'failed'}))
                try:
                    db.delete(file)
                    db.commit()
                except Exception as db_error:
                    db.rollback()
                    r.set(f"task:{self.request.id}:progress",
                          json.dumps({'progress': -1, 'detail': f'Cleanup error: {db_error}', 'status': 'failed'}))

        except Exception:
            pass
        finally:
            db.close()


