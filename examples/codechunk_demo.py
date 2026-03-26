#!/usr/bin/env python3
"""Demo script showing CodeChunk usage."""

import tiktoken

from ws_ctx_engine.models import CodeChunk


def main():
    """Demonstrate CodeChunk functionality."""

    # Create a sample code chunk
    chunk = CodeChunk(
        path="src/utils/math_helpers.py",
        start_line=10,
        end_line=25,
        content="""def calculate_sum(numbers):
    '''Calculate the sum of a list of numbers.'''
    total = 0
    for num in numbers:
        total += num
    return total

def calculate_average(numbers):
    '''Calculate the average of a list of numbers.'''
    if not numbers:
        return 0
    return calculate_sum(numbers) / len(numbers)
""",
        symbols_defined=["calculate_sum", "calculate_average"],
        symbols_referenced=["len"],
        language="python",
    )

    # Display chunk information
    print("CodeChunk Demo")
    print("=" * 60)
    print(f"Path: {chunk.path}")
    print(f"Lines: {chunk.start_line}-{chunk.end_line}")
    print(f"Language: {chunk.language}")
    print(f"Symbols defined: {', '.join(chunk.symbols_defined)}")
    print(f"Symbols referenced: {', '.join(chunk.symbols_referenced)}")
    print()

    # Count tokens using different encodings
    encodings = ["cl100k_base", "p50k_base", "r50k_base"]
    print("Token counts by encoding:")
    print("-" * 60)

    for encoding_name in encodings:
        encoding = tiktoken.get_encoding(encoding_name)
        token_count = chunk.token_count(encoding)
        print(f"{encoding_name:15s}: {token_count:4d} tokens")

    print()
    print("Content preview:")
    print("-" * 60)
    print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)


if __name__ == "__main__":
    main()
