"""Run a standalone district TOP-5 demo using the team's archived 2025 CSV.

Run from repository root: python demo_district.py
Requires pandas and plotly. Does not modify any team member's files.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import shutil

from data_manager import SalesDataManager
from district_comparator import DistrictComparator
from district_visualizer import DistrictVisualizer


ARCHIVE = Path(__file__).with_name("data(23~25).zip")
INDUSTRY_CODE = "CS100001"  # Demo choice; change to any code in get_industry_options().


def main():
    if not ARCHIVE.is_file():
        raise FileNotFoundError(f"Place the team's original archive here: {ARCHIVE}")
    with TemporaryDirectory() as tempdir, ZipFile(ARCHIVE) as zipped:
        name = next((name for name in zipped.namelist() if "2025" in name and name.endswith(".csv")), None)
        if name is None:
            raise FileNotFoundError("No 2025 CSV inside the data archive")
        csv_path = Path(tempdir) / "2025.csv"
        with zipped.open(name) as source, csv_path.open("wb") as destination:
            shutil.copyfileobj(source, destination)

        manager = SalesDataManager([csv_path])
        manager.load_data()
        manager.preprocess_data()
        # Keep all districts for a city-wide ranking.
        records = manager.filter_data(industry=INDUSTRY_CODE, year=2025)
        ranking = DistrictComparator(records).rank_districts(5, "top")
        figure = DistrictVisualizer().plot_ranking(ranking)
        output = Path(__file__).with_name("district_top5_demo.html")
        figure.write_html(str(output))
        print(ranking.to_string(index=False))
        print(f"\nInteractive chart: {output}")


if __name__ == "__main__":
    main()
