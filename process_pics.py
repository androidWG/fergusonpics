import argparse
import functools
import os
import random
from argparse import Namespace
from multiprocessing.pool import ThreadPool
from pathlib import Path

from wand.image import Image

EXTENSIONS = ["png", "jpg", "jpeg", "bmp", "webp", "heic", "heif", "tiff"]


def main(args: Namespace):
    if not args.input.exists() or not args.input.is_dir():
        print(f"Input directory {args.input} does not exist or is not a directory.")
        exit(1)

    if not args.output.is_dir():
        print(f"Output directory {args.output} is not a directory.")
        exit(2)

    if args.clear_output:
        print("Clearing output directory...")
        if args.output.exists():
            for f in args.output.iterdir():
                os.remove(f)

    args.output.mkdir(parents=True, exist_ok=True)

    filtered = [f for f in args.input.iterdir() if f.suffix[1:].lower() in EXTENSIONS]
    numbers = [*range(1, len(filtered) + 1)]

    print("Gathering files...")
    tasks = []
    for filepath in filtered:
        file_id = (
            numbers[random.randint(0, len(numbers) - 1)]
            if len(numbers) > 1
            else numbers[0]
        )
        tasks.append(functools.partial(convert_image, args.output, file_id, filepath))
        numbers.remove(file_id)

    with ThreadPool(args.threads or 1) as pool:
        pool.map(lambda x: x(), tasks)
        pool.close()
        pool.join()


def convert_image(output: Path, name: str, file: Path) -> Path:
    print(f"Processing {file.name}...")

    with Image(filename=file) as img:
        img.format = "webp"
        img.auto_orient()
        img.transform(resize="1000x1000>")

        output_path = output / f"{name}.webp"
        img.save(filename=output_path)

    print(f"\t- Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process and resize images.")
    parser.add_argument("input", help="Input image file path", type=Path)
    parser.add_argument("output", help="Output image file path", type=Path)
    parser.add_argument(
        "-d",
        "--dirty",
        action="store_false",
        help="Do not delete existing output directory files",
        dest="clear_output",
    )
    parser.add_argument(
        "--threads", help="Number of threads to use", type=int, default=os.cpu_count()
    )

    main(parser.parse_args())
