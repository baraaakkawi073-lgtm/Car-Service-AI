# Car-Service-AI — Automatic Vehicle Image Downloader

This package downloads one representative image for every Brand/Model entry in
`Pasted text.txt` and stores the images under:

    image/vehicles/<brand>/<brand>__<model>.webp

It is designed for Windows and is resumable.

## 1. Put the files in your project

Recommended:

    C:\workbench\fast\Car-Service-AI\
        download_car_images.py
        requirements-car-images.txt
        Pasted text.txt

If your catalog file has another name, use `--catalog`.

## 2. Open CMD in the project

    cd /d C:\workbench\fast\Car-Service-AI

## 3. Install dependencies

If your project already has a virtual environment:

    env\Scripts\activate

Then:

    python -m pip install -r requirements-car-images.txt

## 4. Test with only 20 cars first

    python download_car_images.py --limit 20

Check:

    image\vehicles\

If the results look correct, run all entries:

    python download_car_images.py

The downloader is resumable. If it stops, run the same command again.
Existing files are skipped.

## 5. Output

Images:

    image\vehicles\<brand>\*.webp

Source/attribution report:

    image\vehicles\image_sources.csv

The CSV records the Wikimedia Commons file, source URL, description URL,
license metadata when available, and download status.

## Important

The catalog contains many trucks, specialty vehicles, motorcycles, ambiguous
registry entries, and unusual manufacturer names. The script searches
Wikimedia Commons and therefore cannot guarantee that every result is the
exact intended vehicle. Review `image_sources.csv`, especially rows marked
`downloaded`, before publishing the images.

The script deliberately records the original Commons source and license
metadata so you can review reuse conditions.
