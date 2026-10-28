# 직접 받은 2023, 2024, 2025년 CSV를 읽고 정리해 분석 객체에 제공한다.
# 사용 순서: 객체 생성 -> load_data() -> preprocess_data() -> filter_data()
# 원본 열을 유지하고 year(연도), quarter(분기)를 추가한다.

from collections.abc import Iterable
from copy import deepcopy
import csv
from numbers import Integral
from pathlib import Path

import pandas as pd


# 사용하는 열 이름을 상수로 둔다.
PERIOD = "기준_년분기_코드"
DISTRICT_TYPE = "상권_구분_코드"
DISTRICT_TYPE_NAME = "상권_구분_코드_명"
DISTRICT = "상권_코드"
DISTRICT_NAME = "상권_코드_명"
INDUSTRY = "서비스_업종_코드"
INDUSTRY_NAME = "서비스_업종_코드_명"
KEY_COLUMNS = [PERIOD, DISTRICT_TYPE, DISTRICT, INDUSTRY] #같은 데이터인지 구분하는 기준


# 서울시 CSV의 식별 정보 7개 + 금액/건수 지표 48개 = 필요한 원본 열 55개.
# 자료의 대상을 설명하는 열(이 정보들이 비어있는지 검사할 때 사용)
IDENTIFIER_COLUMNS = [
    PERIOD, DISTRICT_TYPE, DISTRICT_TYPE_NAME,
    DISTRICT, DISTRICT_NAME, INDUSTRY, INDUSTRY_NAME,
]
#매출 항목 이름들을 모아둔 목록
METRIC_GROUPS = [
    "당월", "주중", "주말", "월요일", "화요일", "수요일", "목요일",
    "금요일", "토요일", "일요일", "시간대_00~06", "시간대_06~11",
    "시간대_11~14", "시간대_14~17", "시간대_17~21", "시간대_21~24",
    "남성", "여성", "연령대_10", "연령대_20", "연령대_30",
    "연령대_40", "연령대_50", "연령대_60_이상",
]
# 열 이름 만드는 부분
METRIC_COLUMNS = [f"{group}_매출_{kind}" for group in METRIC_GROUPS for kind in ("금액", "건수")]
# CSV에 반드시 있어야 하는 열 이름 목록
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + METRIC_COLUMNS

# 실제 원본 CSV의 시간대 '건수' 열 6개의 이름을 알기쉽게 수정한다.
HEADER_ALIASES = {
    "시간대_건수~06_매출_건수": "시간대_00~06_매출_건수",
    "시간대_건수~11_매출_건수": "시간대_06~11_매출_건수",
    "시간대_건수~14_매출_건수": "시간대_11~14_매출_건수",
    "시간대_건수~17_매출_건수": "시간대_14~17_매출_건수",
    "시간대_건수~21_매출_건수": "시간대_17~21_매출_건수",
    "시간대_건수~24_매출_건수": "시간대_21~24_매출_건수",
}

# ValueError를 상속해서 오류를 새로 정의
class DataValidationError(ValueError):
    # 원본 자료에 분석을 방해하는 오류가 있을 때 발생하는 예외


class SalesDataManager:
    # CSV 읽기, 검증, 전처리, 조건별 데이터 제공을 담당하는 클래스
    
    def __init__(self, file_paths):
        # 파일 경로와 객체 내부에서 사용할 데이터를 보관
        if isinstance(file_paths, (str, Path)):
            file_paths = [file_paths]
        self.file_paths = tuple(Path(path) for path in file_paths)
        if not self.file_paths:
            raise ValueError("CSV 파일 경로를 한 개 이상 지정하세요.")
        self._raw_data = None # CSV에서 읽은 원본 데이터
        self._processed_data = None # 검증 및 전처리 마친 데이터
        self._report = {} # 행 수, 중복, 결측값 등의 검사 결과

    @property
    def processed_data(self):
        #전체 전처리 자료의 복사본. 분석 객체가 공유 원본을 바꾸지 못하게 함
        return self._require_ready().copy()

    @property
    def validation_report(self):
        #행 수, 중복 제거 수, 결측값 등 검증 결과의 복사본
        return deepcopy(self._report)

    def load_data(self):
        # 1단계: 직접 받은 CSV들(23년, 24년, 25년 데이터)을 읽어 하나의 표로 합침
        # ZIP을 받았다면 먼저 압축을 풀고 CSV 경로를 전달
        # UTF-8-SIG로 읽기를 시도하고 한글 해독에 실패하면 CP949로 읽음

        # 생성자에서 초기화 했지만 같은 객체에서 여러번 호출할 수 있기에 한번 더 초기화
        self._raw_data = None
        self._processed_data = None
        self._report = {}

	# 파일마다 읽어온 데이터 표를 모을 곳 / 경로, 인코딩, 행 수를 기록
        frames, file_reports = [], [] 
        
        for path in self.file_paths:
            if not path.is_file():
                raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")
            for encoding in ("utf-8-sig", "cp949"):
                try:
                    # 열 이름을 먼저 확인해 중복 열과 빠진 열을 발견한다.
                    with path.open(encoding=encoding, newline="") as source:
                        raw_headers = next(csv.reader(source), [])
                    headers = [column.strip().lstrip("\ufeff") for column in raw_headers]
                    headers = [HEADER_ALIASES.get(column, column) for column in headers]
                    if len(set(headers)) != len(headers):
                        raise DataValidationError(f"같은 이름의 열이 두 개 이상 있습니다: {path}")
                    missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
                    if missing:
                        raise DataValidationError(f"{path.name}에 필요한 열이 없습니다: {missing}")
                    # 코드를 문자열로 읽어 '000001' 같은 앞자리 0을 유지한다.
                    frame = pd.read_csv(path, encoding=encoding, dtype="string",
                                        keep_default_na=False)
                    break
                except UnicodeDecodeError:
                    if encoding == "cp949":
                        raise DataValidationError(f"UTF-8 또는 CP949로 읽을 수 없습니다: {path}")
             # 전체 표의 열 이름의 앞에서 정리한 열 이름 목록으로 교체
            frame.columns = headers
             # 현재 파일의 정보를 딕셔너리로 만들어서 file_report에 추가
            file_reports.append({"file": str(path), "encoding": encoding, "rows": len(frame)})
            frames.append(frame)
        
        # 각 년도의 행을 이어 붙이고 _raw_data에 저장       
        self._raw_data = pd.concat(frames, ignore_index=True) 
        # 파일별 기록과 전체 행 수를 검사 기록에 저장
        self._report = {"files": file_reports, "input_rows": len(self._raw_data)}
        # 읽어온 전체 표의 복사본을 반환
        return self._raw_data.copy()

    def preprocess_data(self):
        # 2단계: 값을 검사하고 숫자 형식·연도·분기·중복을 정리
        if self._raw_data is None:
            if self._processed_data is not None:
                return self.processed_data
            raise RuntimeError("먼저 load_data()로 CSV를 읽으세요.")
        frame = self._raw_data.copy()
        if frame.empty:
            raise DataValidationError("CSV에 데이터 행이 없습니다.")

        # (1) 식별 정보가 비어 있는지, 기간이 '20241' 같은 형식인지 확인한다.
        for column in IDENTIFIER_COLUMNS:
            frame[column] = frame[column].astype("string").str.strip()
            bad = frame[column].isna() | frame[column].eq("")
            if bad.any():
                raise DataValidationError(f"{column} 값이 없는 행: {int(bad.sum())}개")
        valid_period = frame[PERIOD].str.fullmatch(r"[1-9]\d{3}[1-4]", na=False)
        if not valid_period.all():
            examples = frame.loc[~valid_period, PERIOD].head(3).tolist()
            raise DataValidationError(f"년분기 코드는 20241 같은 형식이어야 합니다: {examples}")

        # (2) 매출·건수를 정수로 바꾼다. 빈 값은 결측값으로 두고 실제 0과 구분한다.
        for column in METRIC_COLUMNS:
            values = frame[column].astype("string").str.strip().str.replace(",", "", regex=False)
            values = values.mask(values.str.lower().isin(["", "-", "na", "n/a", "nan", "null"]))
            # 숫자 검사 뒤 정수로 직접 바꿔 큰 매출액의 반올림 오차를 방지한다.
            valid = values.isna() | values.str.fullmatch(r"\d+(?:\.0+)?", na=False)
            if not valid.all():
                examples = frame.loc[~valid, column].head(3).tolist()
                raise DataValidationError(f"{column}에 음수·소수·숫자가 아닌 값이 있습니다: {examples}")
            try:
                frame[column] = values.str.replace(r"\.0+$", "", regex=True).astype("Int64")
            except (ValueError, OverflowError, TypeError) as error:
                raise DataValidationError(f"{column}의 정수가 저장 가능한 범위를 벗어났습니다.") from error

        # (3) 예: '20251' -> year=2025, quarter=1.
        frame["year"] = frame[PERIOD].str[:4].astype("int64")
        frame["quarter"] = frame[PERIOD].str[4].astype("int64")
        # (4) 완전히 같은 행은 하나만 남기고, 같은 식별 키의 서로 다른 값은 오류로 알린다.
        before_deduplication = len(frame)
        frame = frame.drop_duplicates().reset_index(drop=True)
        conflicts = frame.duplicated(KEY_COLUMNS, keep=False)
        if conflicts.any():
            examples = frame.loc[conflicts, KEY_COLUMNS].head(4).to_dict("records")
            raise DataValidationError(f"같은 기간·상권·업종인데 내용이 다른 행이 있습니다: {examples}")
        frame = frame.sort_values([PERIOD, DISTRICT, INDUSTRY], kind="stable").reset_index(drop=True)
        # (5) 검증 결과와 전처리 자료를 객체 안에 보관한다.
        self._report.update({
            "output_rows": len(frame),
            "exact_duplicates_removed": before_deduplication - len(frame),
            "missing_metrics": {c: int(frame[c].isna().sum()) for c in METRIC_COLUMNS if frame[c].isna().any()},
            "available_periods": sorted(frame[PERIOD].unique().tolist()),
            "district_count": int(frame[DISTRICT].nunique()),
            "industry_count": int(frame[INDUSTRY].nunique()),
        })
        self._processed_data = frame
        self._raw_data = None
        return self.processed_data

    def filter_data(self, district=None, industry=None, year=None, quarter=None,
                    period=None):
        """3단계: 선택 조건을 모두 만족하는 자료의 복사본을 반환한다.

        district/industry에는 상권·업종 '코드'를 넣는다.
        None은 해당 조건 전체, []는 선택 없음이다. 값 하나 또는 목록을 받는다.
        추이 분석에는 여러 분기를, 상권 순위에는 모든 상권을 유지해야 한다.
        """
        frame = self._require_ready()
        mask = pd.Series(True, index=frame.index)  # 각 행을 남길지 True/False로 표시한다.
        for column, selection in [(DISTRICT, district), (INDUSTRY, industry),
                                  ("year", year), ("quarter", quarter), (PERIOD, period)]:
            if selection is None:
                continue
            if isinstance(selection, (str, Integral)):
                selection = [selection]
            elif not isinstance(selection, Iterable):
                raise TypeError(f"{column} 조건에는 값 하나 또는 목록을 넣으세요.")
            selections = list(selection)
            if column in ("year", "quarter"):
                converted = []
                for value in selections:
                    text = str(value).strip()
                    if not text.isdigit():
                        raise ValueError(f"{column} 조건에는 정수를 넣으세요: {value!r}")
                    number = int(text)
                    if column == "quarter" and number not in range(1, 5):
                        raise ValueError("분기는 1~4 중에서 선택하세요.")
                    converted.append(number)
            else:
                converted = [str(value).strip() for value in selections]
            mask &= frame[column].isin(converted)  # 지금까지의 조건과 이번 조건을 모두 적용한다.
        return frame.loc[mask].copy().reset_index(drop=True)

    def get_district_options(self):
      # 4단계: 선택 메뉴에 쓸 상권 코드·이름 목록을 반환
        return self._options(DISTRICT, DISTRICT_NAME)

    def get_industry_options(self):
        """선택 메뉴에 쓸 업종 코드·이름 목록을 반환한다."""
        return self._options(INDUSTRY, INDUSTRY_NAME)

    def get_period_options(self):
        """실제로 존재하는 년분기 코드·연도·분기 목록을 반환한다."""
        return (self._require_ready()[[PERIOD, "year", "quarter"]]
                .drop_duplicates().sort_values(PERIOD).reset_index(drop=True).copy())

    def _options(self, code, name):
        # 같은 코드의 이름이 바뀌었으면 최신 이름을 메뉴에 표시한다.
        return (self._require_ready().sort_values(PERIOD, kind="stable")[[code, name]]
                .drop_duplicates(code, keep="last").sort_values(code)
                .reset_index(drop=True).copy())

    def _require_ready(self):
        if self._processed_data is None:
            raise RuntimeError("먼저 load_data()와 preprocess_data()를 실행하세요.")
        return self._processed_data
