"""Benchmark performance of each screening stage.

The script runs the full screening pipeline on a synthetic image and measures
latency of individual stages. Results are printed and saved to
`performance_report.txt`.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) )
import time
from backend.services import screening_service
from backend.db import database
from backend.db import models

import numpy as np

def generate_image():
    # Simple random image
    return np.full((200, 200, 3), 255, dtype=np.uint8)

def benchmark_one_case(db_session):
    # Create a dummy user and case for benchmarking
    from datetime import datetime
    # Create a dummy user if not exists
    from sqlalchemy.exc import IntegrityError
    user = models.User(id="bench-user", username="benchmark", hashed_password="dummy", role="officer")
    db_session.add(user)
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        # Retrieve existing user
        user = db_session.query(models.User).filter_by(username="benchmark").first()
    # Ensure no existing case with same ID
    existing_case = db_session.query(models.Case).filter_by(id="bench-case").first()
    if existing_case:
        db_session.delete(existing_case)
        db_session.commit()
    case = models.Case(
        id="bench-case",
        owner_id=user.id,
        subject_name="Benchmark",
        created_at=datetime.utcnow(),
        status="created",
    )
    db_session.add(case)
    db_session.commit()
    # Upload a document file record (skip actual file storage)
    # Generate synthetic image and write to temporary file for processing
    import cv2, os
    img = generate_image()
    tmp_path = os.path.abspath("bench_tmp.png")
    cv2.imwrite(tmp_path, img)
    # Simulate file record pointing to real file
    doc = models.DocumentFile(
        id="bench-doc",
        case_id=case.id,
        filename="bench.png",
        stored_path=tmp_path,
        content_hash="dummyhash",
        file_type="document",
    )
    db_session.add(doc)
    db_session.commit()
    # Run screening (async job: enqueue, then wait for the worker to finish)
    start = time.time()
    run = screening_service.create_screening_run(db_session, case_id=case.id, actor_id="benchmark")
    while run.status in ("queued", "running") and (time.time() - start) < 120:
        time.sleep(0.5)
        db_session.expire_all()
        run = db_session.query(models.ScreeningRun).filter_by(id=run.id).first()
    total_ms = (time.time() - start) * 1000
    return run, total_ms

if __name__ == "__main__":
    Session = database.SessionLocal
    db = Session()
    run, total = benchmark_one_case(db)
    report = []
    report.append(f"Total screening time: {total:.2f} ms")
    for sr in run.stage_results:
        report.append(f"Stage {sr.stage}: {sr.processing_time_ms} ms, status={sr.status}")
    txt = "\n".join(report)
    print(txt)
    with open("performance_report.txt", "w") as f:
        f.write(txt)
