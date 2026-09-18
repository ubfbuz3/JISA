#!/usr/bin/env bash
# =============================================================================
# 编译并运行原生 MST-wi 引擎执行 OTG_AUTHZ_*
#   bash build_run.sh [base|augmented]
# 全部产物落在纯 ASCII 目录，规避 Java 8 在中文路径下的编码风险。
# 数据由 gen_inputs.py（离线冒烟）或 run_native.py（真实 Gitea）生成，本脚本不覆盖。
# =============================================================================
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="C:/Users/Administrator/WorkBuddy/mst_native_lab"
WORKP="/c/Users/Administrator/WorkBuddy/mst_native_lab"
ENGINE="/c/Users/Administrator/WorkBuddy/mst_engine"
JAR="C:/Users/Administrator/WorkBuddy/mst_engine/MST/target/MST-1.0.0-jar-with-dependencies.jar"
JAVA="$ENGINE/tools/jdk8u504-b01/bin/java.exe"
JAVAC="$ENGINE/tools/jdk8u504-b01/bin/javac.exe"

MODE="${1:-augmented}"

# Windows 风格路径（喂给 Windows 版 python/java 时必须转换，否则 /c/... 变成 C:\c\...）
win() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else echo "$1"; fi; }

if [ ! -x "$JAVA" ]; then echo "!! 找不到 JDK8: $JAVA"; exit 1; fi
if [ ! -f "$ENGINE/MST/target/MST-1.0.0-jar-with-dependencies.jar" ]; then
  echo "!! 找不到引擎 jar，先跑 mst_engine/build_mst.sh"; exit 1
fi

# --- 1. 源码复制到 ASCII 目录（编译期不触碰中文路径） ---------------------
rm -rf "$WORKP/classes" "$WORKP/out"
mkdir -p "$WORKP/src" "$WORKP/classes" "$WORKP/out"
rm -rf "$WORKP/src"
mkdir -p "$WORKP/src"
cp -r "$HERE/src/." "$WORKP/src/"

echo "=== 编译 ==="
SRCS="$(cd "$WORKP" && find src -name '*.java')"
( cd "$WORKP" && "$JAVAC" -encoding UTF-8 -source 1.8 -target 1.8 \
    -nowarn -cp "$JAR" -d "$WORK/classes" $SRCS ) || { echo "!! 编译失败"; exit 1; }
echo "    ok: $(find "$WORKP/classes" -name '*.class' | wc -l) 个 class"

# --- 2. 数据缺失时用离线生成器兜底（真实实验由 run_native.py 负责） --------
if [ ! -f "$WORKP/data/config.json" ]; then
  echo "=== 生成引擎数据（离线兜底） ==="
  PY="${PY:-C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe}"
  [ -x "$PY" ] || PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
  "$PY" "$(win "$HERE/gen_inputs.py")" || { echo "!! 数据生成失败"; exit 1; }
fi

PAIR="$WORK/data/pairing.json"
[ -f "$WORKP/data/pairing.json" ] || PAIR="-"

# --- 3. 运行 ---------------------------------------------------------------
echo "=== 运行（mode=$MODE） ==="
"$JAVA" -Dfile.encoding=UTF-8 \
  -cp "$WORK/classes;$JAR" \
  smrl.mr.crawljax.RunAuthzMRs \
  "$WORK/data/config.json" "$WORK/out/result_${MODE}.json" "$PAIR" "$MODE"
RC=$?

echo "=== 产出 ==="
ls -la "$WORKP/out/" 2>/dev/null
exit $RC
