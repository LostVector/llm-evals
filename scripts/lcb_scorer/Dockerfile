FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN pip install --no-cache-dir numpy==2.3.5 tqdm==4.67.1
COPY lcb_runner /opt/lcb/lcb_runner
COPY score.py /opt/lcb/score.py
ENV PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /opt/lcb
USER 65534:65534
ENTRYPOINT ["python", "/opt/lcb/score.py"]
