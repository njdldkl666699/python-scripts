import argparse
import asyncio
from pathlib import Path
from types import CoroutineType
from typing import Any

from copilot import CopilotClient, CopilotSession
from copilot.generated.session_events import AssistantMessageData, SessionEvent
from copilot.session import FileAttachment, PermissionHandler
from loguru import logger


async def safe_send_and_wait(session: CopilotSession, attachment: FileAttachment):
    try:
        return await session.send_and_wait(
            "请分析这篇论文并输出中文结果",
            attachments=[attachment],
            timeout=300,
        )
    except Exception as e:
        display_name = attachment.get("displayName", "unknown")
        logger.error("Error analyzing paper '{}': {}", display_name, e)
        return None


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Batch analyze papers and generate a Markdown report for each paper.")
    )
    parser.add_argument(
        "paper_dir",
        help="Directory containing the papers to analyze.",
    )
    parser.add_argument(
        "-O",
        "--output-dir",
        dest="output_dir",
        required=True,
        help="Directory to write Markdown reports into.",
    )
    args = parser.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    papers: list[FileAttachment] = []
    for paper_path in paper_dir.iterdir():
        if paper_path.is_file():
            papers.append(
                {
                    "type": "file",
                    "path": str(paper_path.resolve()),
                    "displayName": paper_path.name,
                }
            )

    async with CopilotClient() as client:
        sessions: list[CopilotSession] = []
        for _ in papers:
            session = await client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model="gpt-5.2",
                reasoning_effort="high",
                system_message={
                    "mode": "replace",
                    "content": Path("./Paper Analyzer.md").read_text(encoding="utf-8"),
                },
                available_tools=["*"],
            )
            sessions.append(session)

        paper_analysis_tasks: list[CoroutineType[Any, Any, SessionEvent | None]] = []
        for session, paper in zip(sessions, papers):
            paper_analysis_tasks.append(safe_send_and_wait(session, paper))
        session_events = await asyncio.gather(*paper_analysis_tasks)

    for i, event in enumerate(session_events):
        if not event or not isinstance(event.data, AssistantMessageData):
            logger.warning("No valid response for paper: {}", papers[i]["path"])
            continue

        report_content = event.data.content
        paper_name = Path(papers[i]["path"]).stem
        output_path = output_dir / f"{paper_name}_analysis.md"
        output_path.write_text(report_content, encoding="utf-8")
        logger.info("Report for paper '{}' written to: {}", paper_name, output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
