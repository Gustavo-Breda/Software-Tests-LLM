import sys

from .context_builder import ContextBuilder, verify_complete, REQUIRED_SECTIONS


def main() -> int:
    builder = ContextBuilder.from_repo()
    stories = builder.list_stories()
    if not stories:
        print("ERRO: nenhuma story encontrada em data/user_stories/", file=sys.stderr)
        return 2

    print(f"Verificando {len(stories)} story/ies — seções requeridas: "
          f"{len(REQUIRED_SECTIONS)}\n")

    all_ok = True
    rows: list[tuple[str, bool, int, int, int]] = []

    for sid in stories:
        blob = builder.build(sid)
        result = verify_complete(blob)
        rows.append((sid, result.ok, result.char_count, result.token_estimate,
                     len(blob.story.acceptance_criteria)))

        status = "✅ OK" if result.ok else "❌ FALHOU"
        print(f"== {sid}: {status}")
        print(f"   chars={result.char_count}  ~tokens={result.token_estimate}  "
              f"criterios={len(blob.story.acceptance_criteria)}")
        if result.missing_sections:
            print(f"   Seções faltando: {result.missing_sections}")
            all_ok = False
        for note in result.notes:
            print(f"   ⚠️  {note}")
            all_ok = False
        print()

    print("Resumo")
    print(f"  {'Story':<8} {'OK':<4} {'Chars':>7} {'~Tokens':>9} {'Critérios':>10}")
    for sid, ok, chars, toks, crit in rows:
        mark = "sim" if ok else "NÃO"
        print(f"  {sid:<8} {mark:<4} {chars:>7} {toks:>9} {crit:>10}")

    if not all_ok:
        print("\nUma ou mais stories falharam na verificação.", file=sys.stderr)
        return 1
    print("\nTodas as stories produziram blobs completos. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
