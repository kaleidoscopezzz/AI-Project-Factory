"""Installed product command; factory core stays responsible for all approvals."""
import json
from datetime import datetime
from pathlib import Path

from . import APFError


def build(args):
    from factory.contracts import FactoryError
    from factory.executor import CodexExecutor
    from factory.product import ProductRun
    from .codex import discover_codex, preflight
    from .skills import discover_skills
    try:
        if not args.full_access:
            raise APFError('--build 需要显式 --full-access：当前用户文件、进程和网络权限，没有OS工作区隔离。')
        if args.timeout > 600:
            raise APFError('--build / --resume 单次Agent超时最多600秒')
        if args.resume and args.out:
            raise APFError('--resume 自带原输出目录，不与 --out 组合')
        if args.out is not None and not args.out.strip():
            raise APFError('--out 目录不能为空')
        output=Path(args.resume or args.out or ('apf-build-'+datetime.now().strftime('%Y%m%d-%H%M%S'))).absolute()
        selected=None if args.resume else discover_skills(args.skills_dir)
        # Check flags before CLI resolution; metadata checks never start a model.
        exe=discover_codex(args.codex_path)
        # The parent exists for readonly metadata checks. Do not precreate the
        # actual output: ProductRun creates it exclusively after validation.
        parent=output.parent
        if not parent.is_dir(): raise APFError('输出父目录不存在；请先建立父目录')
        preflight(exe,parent)
        native=CodexExecutor(full_access=False,codex_path=str(exe))
        run=ProductRun(output,request=args.build,resume=bool(args.resume),full_access=args.full_access,
                       allow_local_git=args.allow_local_git,executor=native,skills=selected,timeout=args.timeout)
        print('权限：Planner/Reviewer只读，Coder/Tester当前用户Full Access。最多2个Goal、1次返工、10次模型调用、整轮3600秒；Token无硬上限。',flush=True)
        result=run.execute()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    except FactoryError as exc:
        raise APFError(str(exc)) from exc
