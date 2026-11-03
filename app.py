# Run with: streamlit run app.py
# Entry point: creates the objects and passes them to DashboardManager.

from pathlib import Path
import importlib
import zipfile

import streamlit as st

import dashboard_manager
import ui_text
from data_manager import SalesDataManager

# Streamlit does not always notice edits to imported modules (seen on Windows),
# so the UI modules are reloaded on every rerun. Cheap, and data stays cached.
importlib.reload(ui_text)
importlib.reload(dashboard_manager)
DashboardManager = dashboard_manager.DashboardManager

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_ZIP = BASE_DIR / "data(23~25).zip"


def find_csv_files():
    # If the data folder has no CSV files yet, extract them from the ZIP in the repository.
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files and DATA_ZIP.is_file():
        with zipfile.ZipFile(DATA_ZIP) as archive:
            archive.extractall(DATA_DIR)
        files = sorted(DATA_DIR.glob("*.csv"))
    return files


@st.cache_resource(show_spinner="Loading data... (first run only)")
def load_data_manager():
    manager = SalesDataManager(find_csv_files())
    manager.load_data()
    manager.preprocess_data()
    return manager


def load_team_classes():
    # Each teammate's class is used as soon as its file is in the folder (after git pull).
    # A missing class leaves its sections out of the dashboard.
    team = {}
    sources = {
        "sales_analyzer": ("sales_analyzer", "SalesAnalyzer"),
        "sales_visualizer": ("sales_visualizer", "SalesVisualizer"),
        "demographic_analyzer": ("demographic_analyzer", "DemographicAnalyzer"),
        "demographic_visualizer": ("demographic_visualizer", "DemographicVisualizer"),
        "district_comparator": ("district_comparator", "DistrictComparator"),
        "district_visualizer": ("district_visualizer", "DistrictVisualizer"),
    }
    for name, (module_name, class_name) in sources.items():
        try:
            module = importlib.reload(importlib.import_module(module_name))
            team[name] = getattr(module, class_name)
        except (ImportError, AttributeError):
            team[name] = None
    return team


def build_dashboard():
    data_manager = load_data_manager()
    team = load_team_classes()
    # Analyzers are passed as classes (created per data selection: SalesAnalyzer(data));
    # visualizers are created once here.
    objects = {name: (cls() if cls is not None and name.endswith("visualizer") else cls)
               for name, cls in team.items()}
    return DashboardManager(data_manager, **objects)


st.set_page_config(page_title="Seoul District Sales Dashboard", page_icon="📊", layout="wide")
build_dashboard().run()
