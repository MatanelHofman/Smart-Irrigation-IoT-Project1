"""Fill in the demo video and presentation recording links in the PPTX.

Usage:
    python deliverables/update_presentation_links.py \\
        --video-link https://example.com/demo-video \\
        --recording-link https://example.com/presentation-recording

Replaces the [ADD_DEMO_VIDEO_LINK] and [ADD_PRESENTATION_RECORDING_LINK]
placeholders on slide 11 in place, turns the new text into a clickable
hyperlink, and keeps every other slide untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation

PPTX_PATH = Path(__file__).resolve().parent / "Smart_Irrigation_Project_Presentation_HE.pptx"

PLACEHOLDERS = {
    "[ADD_DEMO_VIDEO_LINK]": "video_link",
    "[ADD_PRESENTATION_RECORDING_LINK]": "recording_link",
}


def replace_placeholder(prs: Presentation, placeholder: str, url: str) -> bool:
    replaced = False
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, url)
                        run.hyperlink.address = url
                        replaced = True
    return replaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-link", help="URL of the short demo video")
    parser.add_argument("--recording-link", help="URL of the full presentation recording")
    parser.add_argument("--pptx", default=str(PPTX_PATH), help="Path to the presentation file")
    args = parser.parse_args()

    if not args.video_link and not args.recording_link:
        parser.error("provide at least one of --video-link / --recording-link")

    prs = Presentation(args.pptx)

    if args.video_link:
        found = replace_placeholder(prs, "[ADD_DEMO_VIDEO_LINK]", args.video_link)
        print("Updated demo video link." if found else "Demo video placeholder not found (already updated?).")

    if args.recording_link:
        found = replace_placeholder(prs, "[ADD_PRESENTATION_RECORDING_LINK]", args.recording_link)
        print("Updated recording link." if found else "Recording placeholder not found (already updated?).")

    prs.save(args.pptx)
    print(f"Saved: {args.pptx}")


if __name__ == "__main__":
    main()
