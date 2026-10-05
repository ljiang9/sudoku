"""数独求解与校验小工具。

- solver: 带 MRV（最少剩余值）启发式的回溯搜索。普通谜题 <1 秒。
- validate: 检查 9x9 网格是否合法（无行/列/宫重复）。
- check: 验证解是否与谜题相符且合法。

纯标准库：argparse / sys / json。
"""
import argparse
import json
import sys

EMPTY = set("0._")


def parse_grid(text, source="<输入>"):
    """解析 9x9 网格文本。返回 81 格整数列表（0=空），格式错误抛 ValueError。"""
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    # 去掉空行
    rows = [ln for ln in lines if ln.strip()]
    if len(rows) != 9:
        raise ValueError(f"{source}：需要 9 行数据，实际 {len(rows)} 行")
    cells = []
    for i, ln in enumerate(rows, 1):
        ln = ln.replace(" ", "")
        if len(ln) != 9:
            raise ValueError(f"{source}：第 {i} 行需要 9 个字符，实际 {len(ln)} 个")
        for ch in ln:
            if ch.isdigit():
                cells.append(int(ch))
            elif ch in EMPTY:
                cells.append(0)
            else:
                raise ValueError(f"{source}：第 {i} 行有非法字符 '{ch}'（只允许 0-9 或 0/._ 表示空格）")
    return cells


def format_grid(cells, pretty=False):
    if not pretty:
        return "\n".join("".join(str(c) for c in cells[r * 9:(r + 1) * 9]) for r in range(9))
    out = []
    for r in range(9):
        if r in (3, 6):
            out.append("───────┼───────┼───────")
        row = []
        for c in range(9):
            if c in (3, 6):
                row.append("│")
            v = cells[r * 9 + c]
            row.append(str(v) if v else "·")
        out.append(" ".join(row))
    return "\n".join(out)


def find_duplicate(cells):
    """返回首个冲突 (类型, 编号, 数字)，无冲突返回 None。"""
    for r in range(9):
        seen = set()
        for c in range(9):
            v = cells[r * 9 + c]
            if v:
                if v in seen:
                    return ("行", r + 1, v)
                seen.add(v)
    for c in range(9):
        seen = {}
        for r in range(9):
            v = cells[r * 9 + c]
            if v and v in seen:
                return ("列", c + 1, v)
            if v:
                seen[v] = True
    for br in range(3):
        for bc in range(3):
            seen = {}
            for dr in range(3):
                for dc in range(3):
                    v = cells[(br * 3 + dr) * 9 + (bc * 3 + dc)]
                    if v and v in seen:
                        return ("宫", br * 3 + bc + 1, v)
                    if v:
                        seen[v] = True
    return None


def candidates(cells, idx):
    r, c = divmod(idx, 9)
    used = set()
    for k in range(9):
        used.add(cells[r * 9 + k])
        used.add(cells[k * 9 + c])
    br, bc = (r // 3) * 3, (c // 3) * 3
    for dr in range(3):
        for dc in range(3):
            used.add(cells[(br + dr) * 9 + (bc + dc)])
    return {d for d in range(1, 10)} - used


def solve(cells):
    """MRV 回溯求解。返回解（81 格列表）或 None（无解）。"""
    cells = list(cells)
    empties = [i for i, v in enumerate(cells) if v == 0]

    def search():
        # MRV：选候选数最少的空格
        best, best_cands = -1, None
        for i in empties:
            if cells[i] != 0:
                continue
            cand = candidates(cells, i)
            if not cand:
                return False
            if best_cands is None or len(cand) < len(best_cands):
                best, best_cands = i, cand
                if len(cand) == 1:
                    break
        if best == -1:
            return True  # 全填满
        for d in sorted(best_cands):
            cells[best] = d
            if search():
                return True
            cells[best] = 0
        return False

    return cells if search() else None


def cmd_solve(args):
    try:
        cells = parse_grid(open(args.file, encoding="utf-8").read(), args.file)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    dup = find_duplicate(cells)
    if dup:
        print(f"error: 谜题本身不合法：{dup[0]}{dup[1]} 中数字 {dup[2]} 重复", file=sys.stderr)
        return 1
    import time
    t0 = time.monotonic()
    sol = solve(cells)
    ms = (time.monotonic() - t0) * 1000
    if sol is None:
        print("无解：该谜题不存在合法填充。", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"solution": sol, "ms": round(ms, 1)}, ensure_ascii=False))
    else:
        print(format_grid(sol, pretty=args.pretty))
        print(f"\n（求解用时 {ms:.1f} ms）", file=sys.stderr)
    return 0


def cmd_validate(args):
    try:
        cells = parse_grid(open(args.file, encoding="utf-8").read(), args.file)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    dup = find_duplicate(cells)
    filled = sum(1 for v in cells if v)
    result = {"valid": dup is None, "filled": filled}
    if dup:
        result["reason"] = f"{dup[0]}{dup[1]} 中数字 {dup[2]} 重复"
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif dup:
        print(f"❌ 不合法：{result['reason']}")
    else:
        suffix = "（已填满，是完整解）" if filled == 81 else f"（已填 {filled}/81 格，可继续）"
        print(f"✅ 合法{suffix}")
    return 0 if dup is None else 1


def cmd_check(args):
    try:
        puzzle = parse_grid(open(args.puzzle, encoding="utf-8").read(), args.puzzle)
        sol = parse_grid(open(args.solution, encoding="utf-8").read(), args.solution)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for i in range(81):
        if puzzle[i] and puzzle[i] != sol[i]:
            r, c = divmod(i, 9)
            print(f"❌ 解与谜题不符：第 {r+1} 行第 {c+1} 列，谜题是 {puzzle[i]}，解写成 {sol[i]}")
            return 1
    if any(v == 0 for v in sol):
        print("❌ 解不完整：还有空格未填")
        return 1
    dup = find_duplicate(sol)
    if dup:
        print(f"❌ 解不合法：{dup[0]}{dup[1]} 中数字 {dup[2]} 重复")
        return 1
    print("✅ 解正确：与谜题相符且合法")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sudoku", description="数独求解与校验小工具")
    ap.add_argument("--version", action="version", version="sudoku 0.1.0")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("solve", help="求解数独")
    p.add_argument("file", help="谜题文件（9x9，0/._ 表示空格）")
    p.add_argument("--pretty", action="store_true", help="宫线分隔的美化输出")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("validate", help="校验网格是否合法")
    p.add_argument("file", help="网格文件")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("check", help="验证解是否正确")
    p.add_argument("puzzle", help="谜题文件")
    p.add_argument("solution", help="解文件")
    p.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
