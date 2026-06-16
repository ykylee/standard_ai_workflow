"""tools — script + helper module collection (v0.7.56+).

`sources under workflow-source/tools/` (e.g. score_wiki_trend.py,
release_pipeline.py) 는 *script* 로 작성되어 import 가 안 됨. v0.7.55 에서
in-process wrapper (release_pipeline_lib.py) 로 한 가지 우회, v0.7.56 에서
*본 __init__.py* 추가로 모든 tools script 가 `tools.<name>` 로 import 가능.

Before:
    sys.path.insert(0, str(tools_dir))
    spec = importlib.util.spec_from_file_location("tools_release_pipeline", ...)

After:
    import tools.score_wiki_trend
    import tools.release_pipeline_lib

`tools/` 가 package 로 인식되려면 본 file 존재 필수 (Python 3.x PEP 328).
"""
