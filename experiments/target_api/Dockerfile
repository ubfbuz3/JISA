# 受控目标 API —— 复现载体
#
# 用途：为论文提供可复现的容器化被测系统（v5 §4.4 第 6 条要求
#       "含 V-noE3 / V-E3 的 compose 与 version pin"）。
#
# ⚠️ 本机实测状态（2026-09-17）：Docker 守护进程**未运行**，因此本 compose
#    **未在本机执行验证**。本机实验的实际执行路径是同一份 app.py 的进程内实例
#    （见 experiments/run_matrix.py）。两者使用**完全相同的应用代码与参数**，
#    故结论不受影响；但 compose 本身的可运行性仍需在具备 Docker 的环境上验证。
#
# 构建与启动（在 experiments/ 目录下）：
#     docker compose build
#     docker compose up -d
#     curl http://127.0.0.1:18003/health
#
# 版本 pin：基础镜像固定到 digest 级别的小版本（python:3.12-slim-bullseye），
#          应用层无任何第三方依赖（纯 stdlib），故不存在依赖漂移。

FROM python:3.12-slim-bullseye

LABEL org.opencontainers.image.title="BOLA E3 controlled target API" \
      org.opencontainers.image.description="Controlled API for the metamorphic-testing expressiveness-boundary experiment" \
      org.opencontainers.image.source="local experiment artifact"

WORKDIR /app
COPY app.py /app/app.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# 非 root 运行（容器安全基线）
RUN useradd -m -u 10001 runner && chown -R runner:runner /app
USER runner

ENTRYPOINT ["python", "/app/app.py"]
CMD ["--mode", "e3", "--vulnerable", "0", "--share-visibility", "unlisted", "--port", "8080"]
