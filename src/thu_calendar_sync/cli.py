from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from thu_calendar_sync.config import load_config, load_state, save_state
from thu_calendar_sync.exceptions import ThuCalSyncError

app = typer.Typer(name="thu-cal", help="清华课表 → Outlook 日历同步工具")
console = Console()


def _get_config(config_path: Path | None = None):
    cfg = load_config(config_path)
    errors = cfg.validate()
    if errors:
        for e in errors:
            console.print(f"[yellow]⚠[/yellow] {e}")
    return cfg


@app.command()
def login(
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
):
    """测试登录清华统一身份认证。"""
    cfg = _get_config(config_path)
    if not cfg.username or not cfg.password:
        console.print("[red]✗[/red] 未配置用户名或密码")
        raise typer.Exit(1)

    state = load_state()
    fp = state.get("fingerprint", "")
    f3 = state.get("finger3", "")

    console.print(f"正在登录 [cyan]{cfg.username}[/cyan]...")
    try:
        from thu_calendar_sync.auth import login as do_login
        from thu_calendar_sync.exceptions import TwoFactorRequiredError
        try:
            auth = do_login(cfg.username, cfg.password, fingerprint=fp, finger3=f3)
        except TwoFactorRequiredError:
            console.print("[yellow]需要二次认证[/yellow]")
            auth = do_login(cfg.username, cfg.password, fingerprint=fp, finger3=f3)
        console.print(f"[green]✓[/green] 登录成功，CSRF token: {auth.csrf_token[:16]}...")

        if auth.fingerprint or auth.finger3:
            state["fingerprint"] = auth.fingerprint or fp
            state["finger3"] = auth.finger3 or f3
            save_state(state)
            console.print("[green]✓[/green] 信任设备信息已保存")
    except ThuCalSyncError as e:
        console.print(f"[red]✗[/red] 登录失败: {e}")
        raise typer.Exit(1)


@app.command()
def sync(
    start: Annotated[Optional[str], typer.Option("--start", "-s")] = None,
    end: Annotated[Optional[str], typer.Option("--end", "-e")] = None,
    graduate: Annotated[bool, typer.Option("--graduate")] = False,
    reminder: Annotated[Optional[int], typer.Option("--reminder", "-r", help="提前提醒分钟数")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
):
    """同步课表到 Outlook 日历。默认 dry-run 模式。"""
    cfg = _get_config(config_path)
    if graduate:
        cfg.graduate = True

    console.print(Panel("[bold]清华课表同步[/bold]", subtitle="thu-calendar-sync v0.1"))

    console.print("正在登录...")
    from thu_calendar_sync.auth import login as do_login
    state = load_state()
    fp = state.get("fingerprint", "")
    f3 = state.get("finger3", "")
    if fp and f3:
        console.print("  使用已保存的信任设备信息...")
    auth = do_login(cfg.username, cfg.password, fingerprint=fp, finger3=f3)
    console.print("[green]✓[/green] 登录成功")

    if auth.fingerprint or auth.finger3:
        state["fingerprint"] = auth.fingerprint or fp
        state["finger3"] = auth.finger3 or f3
        save_state(state)
        if not fp:
            console.print("[green]✓[/green] 信任设备信息已保存（下次登录将跳过 2FA）")

    if not start or not end:
        console.print("正在获取学期信息...")
        from thu_calendar_sync.fetcher import get_current_semester
        semester = get_current_semester(auth.session, auth.csrf_token)
        start = start or semester["start_date"]
        end = end or semester["end_date"]
        console.print(f"  学期: {start} → {end}")

    console.print(f"正在获取课表 ({start} → {end})...")
    from thu_calendar_sync.fetcher import fetch_calendar
    events = fetch_calendar(auth, start, end, cfg.graduate)
    console.print(f"[green]✓[/green] 获取到 {len(events)} 条课程事件")

    if events:
        table = Table(title="课程事件预览", show_lines=False)
        table.add_column("课程", style="cyan")
        table.add_column("日期", style="green")
        table.add_column("时间", style="yellow")
        table.add_column("地点", style="magenta")
        shown = set()
        for ev in events:
            key = (ev.course_name, ev.start_time, ev.end_time, ev.location)
            if key not in shown:
                table.add_row(ev.course_name, ev.date, f"{ev.start_time}-{ev.end_time}", ev.location)
                shown.add(key)
        console.print(table)

    if dry_run:
        console.print("\n[yellow]DRY-RUN 模式[/yellow] — 使用 --execute 执行同步")
        return

    output_dir = Path.cwd() / "output"
    semester_label = f"{start}_{end}"
    output_file = output_dir / f"课表_{semester_label}.ics"

    console.print(f"\n正在生成 .ics 文件...")
    from thu_calendar_sync.ics_writer import save_ics
    save_ics(events, output_file, semester_label=f"{start}~{end}", reminder_minutes=reminder)
    console.print(f"[green]✓[/green] 已生成 {len(events)} 条事件")
    console.print(f"  文件: [cyan]{output_file}[/cyan]")
    console.print(f"\n双击 [cyan]{output_file.name}[/cyan] 即可导入到 Outlook 日历")


@app.command()
def status(
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
):
    """显示同步状态。"""
    cfg = _get_config(config_path)
    state = load_state()

    table = Table(title="同步状态")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")

    table.add_row("学号", cfg.username or "(未配置)")
    table.add_row("研究生", "是" if cfg.graduate else "否")
    table.add_row("学期起止", f"{cfg.semester_start or '(自动)'} → {cfg.semester_end or '(自动)'}")
    table.add_row("上次同步", state.get("last_sync", "(从未同步)"))
    table.add_row("事件数量", str(len(state.get("events", {}))))

    console.print(table)
