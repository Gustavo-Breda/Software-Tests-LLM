import sys

from . import ContextBuilder


def _cli(argv: list[str]) -> int:
    builder = ContextBuilder.from_repo()
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: python -m pipeline.context.context_builder [--list | --all | <story_id>]")
        print(f"Stories disponíveis: {', '.join(builder.list_stories()) or '(nenhuma)'}")
        return 0
    if argv[0] == "--list":
        for sid in builder.list_stories():
            print(sid)
        return 0
    if argv[0] == "--all":
        for blob in builder.build_all():
            print(blob.text)
            print("\n\n" + "=" * 80 + "\n\n")
        return 0
    story_id = argv[0]
    try:
        blob = builder.build(story_id)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(blob.text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli(sys.argv[1:]))
