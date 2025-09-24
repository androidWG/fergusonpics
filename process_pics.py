import argparse
import functools
import os
import random
from argparse import Namespace
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any

from wand.image import Image

EXTENSIONS = ["png", "jpg", "jpeg", "bmp", "webp", "heic", "heif", "tiff"]


def main(args: Namespace):
    if not args.output.is_dir():
        print(f"Output directory {args.output} is not a directory.")
        exit(2)

    if args.command == "rebuild" or args.command == "append":
        if not args.input.exists() or not args.input.is_dir():
            print(f"Input directory {args.input} does not exist or is not a directory.")
            exit(1)

        if args.clear_output:
            print("Clearing output directory...")
            if args.output.exists():
                for f in args.output.iterdir():
                    os.remove(f)

        args.output.mkdir(parents=True, exist_ok=True)

    match args.command:
        case "delete":
            existing = [
                f for f in args.output.iterdir() if f.suffix[1:].lower() in EXTENSIONS
            ]

            to_delete = [args.output / f"{num}.webp" for num in args.images]
            for file in to_delete:
                if file in existing:
                    print(f"Deleting {file.name}...")
                    os.remove(file)
                    existing.remove(file)
                else:
                    print(
                        f"File {file.name} does not exist in output directory, ignoring."
                    )

            existing.sort(key=lambda x: int(x.stem))
            for index, file in enumerate(existing, start=1):
                new_name = args.output / f"{index}.webp"
                if file != new_name:
                    print(f"Renaming {file.name} to {new_name.name}...")
                    file.rename(new_name.absolute())

            return
        case "rebuild":
            filtered = [
                f for f in args.input.iterdir() if f.suffix[1:].lower() in EXTENSIONS
            ]
            numbers = [*range(1, len(filtered) + 1)]
            tasks = create_tasks(args, filtered, numbers)
        case "append":
            if args.images:
                filtered = [
                    f for f in args.images if f.suffix[1:].lower() in EXTENSIONS
                ]
            else:
                filtered = [
                    f
                    for f in args.input.iterdir()
                    if f.suffix[1:].lower() in EXTENSIONS
                ]

            if len(filtered) == 0:
                print("No valid image files provided.")
                exit(3)

            existing_numbers = [
                int(f.stem) for f in args.output.iterdir() if f.suffix == ".webp"
            ]
            max_number = max(existing_numbers) if existing_numbers else 0
            numbers = [*range(max_number + 1, max_number + len(filtered) + 1)]

            tasks = create_tasks(args, filtered, numbers)
        case _:
            print("No valid command provided.")
            exit(4)

    with ThreadPool(args.threads or 1) as pool:
        pool.map(lambda x: x(), tasks)
        pool.close()
        pool.join()


def create_tasks(args: Namespace, filtered: list[Any], numbers: list[Any]) -> list[Any]:
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
    return tasks


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
    parser.add_argument("output", help="Folder with images for the website", type=Path)
    subparsers = parser.add_subparsers(dest="command")

    rebuild = subparsers.add_parser("rebuild", help="Rebuild image directory")
    rebuild.add_argument("input", help="Input folder path", type=Path)
    rebuild.add_argument(
        "-d",
        "--dirty",
        action="store_false",
        help="Do not delete existing output directory files",
        dest="clear_output",
    )
    rebuild.add_argument(
        "--threads", help="Number of threads to use", type=int, default=os.cpu_count()
    )

    delete = subparsers.add_parser("delete", help="Delete output images")
    delete.add_argument(
        "images",
        nargs="+",
        type=int,
        help="List of image numbers to delete",
    )

    append = subparsers.add_parser("append", help="Add images to the end of the list")
    append.add_argument(
        "images", nargs="+", type=Path, help="List of image files to add"
    )
    append.add_argument("-i", "--input", help="Input folder path", type=Path)
    append.add_argument(
        "--threads", help="Number of threads to use", type=int, default=os.cpu_count()
    )

    main(parser.parse_args())
