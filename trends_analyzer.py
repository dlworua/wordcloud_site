"""
Google Trends 데이터 수집 및 분석 모듈
보험 키워드의 검색 트렌드를 시간대별, 요일별, 주별, 월별로 분석
"""

from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime, timedelta
import time
from keywords_config import PRODUCT_KEYWORDS, PRODUCT_CATEGORIES

class TrendsAnalyzer:
    """Google Trends 데이터 분석 클래스"""

    def __init__(self):
        """pytrends 객체 초기화"""
        self.pytrends = TrendReq(hl='ko', tz=540)  # 한국 시간대 (UTC+9)

    def fetch_trends_data(self, keywords, timeframe='today 3-m', geo='KR'):
        """
        Google Trends에서 키워드 검색 트렌드 데이터 수집

        Args:
            keywords (list): 검색할 키워드 리스트 (최대 5개)
            timeframe (str): 기간 설정
                - 'now 1-H': 최근 1시간
                - 'now 4-H': 최근 4시간
                - 'now 1-d': 최근 1일
                - 'now 7-d': 최근 7일
                - 'today 1-m': 최근 1개월
                - 'today 3-m': 최근 3개월
                - 'today 12-m': 최근 12개월
            geo (str): 지역 코드 ('KR' = 한국)

        Returns:
            pandas.DataFrame: 시간별 검색 트렌드 데이터
        """
        try:
            # Google Trends API 호출 제한을 피하기 위한 딜레이
            time.sleep(1)

            # 키워드 빌드 (최대 5개까지만 가능)
            keywords = keywords[:5]
            self.pytrends.build_payload(
                keywords,
                cat=0,  # 카테고리 (0 = 전체)
                timeframe=timeframe,
                geo=geo,
                gprop=''  # 검색 유형 ('' = 웹 검색)
            )

            # 시간별 관심도 데이터 가져오기
            interest_over_time = self.pytrends.interest_over_time()

            if not interest_over_time.empty:
                # 'isPartial' 컬럼 제거 (부분 데이터 플래그)
                if 'isPartial' in interest_over_time.columns:
                    interest_over_time = interest_over_time.drop(columns=['isPartial'])

            return interest_over_time

        except Exception as e:
            print(f"트렌드 데이터 수집 오류: {e}")
            return pd.DataFrame()

    def get_related_queries(self, keyword):
        """
        특정 키워드의 연관 검색어 가져오기

        Args:
            keyword (str): 검색할 키워드

        Returns:
            dict: 상승 검색어와 인기 검색어
        """
        try:
            time.sleep(1)
            self.pytrends.build_payload([keyword], timeframe='today 3-m', geo='KR')
            related_queries = self.pytrends.related_queries()
            return related_queries.get(keyword, {})
        except Exception as e:
            print(f"연관 검색어 수집 오류: {e}")
            return {}

    def analyze_by_category(self, timeframe='today 3-m'):
        """
        카테고리별 검색 트렌드 분석

        Args:
            timeframe (str): 분석 기간

        Returns:
            dict: 카테고리별 평균 검색량
        """
        category_scores = {}

        for category in PRODUCT_CATEGORIES:
            # 카테고리 이름을 키워드로 사용
            df = self.fetch_trends_data([category], timeframe=timeframe)

            if not df.empty and category in df.columns:
                # 평균 검색량 계산
                category_scores[category] = df[category].mean()
            else:
                category_scores[category] = 0

        return category_scores

    def analyze_by_time(self, keywords, timeframe='now 7-d'):
        """
        시간대별 검색 트렌드 분석

        Args:
            keywords (list): 분석할 키워드 리스트
            timeframe (str): 분석 기간

        Returns:
            pandas.DataFrame: 시간대별 검색량
        """
        df = self.fetch_trends_data(keywords, timeframe=timeframe)

        if df.empty:
            return pd.DataFrame()

        # 시간 정보 추가
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek  # 0=월요일, 6=일요일
        df['date'] = df.index.date

        return df

    def get_hourly_analysis(self, keywords, days=7):
        """
        시간대별 평균 검색량 분석 (0-23시)

        Args:
            keywords (list): 분석할 키워드
            days (int): 분석할 일수

        Returns:
            dict: 시간대별 평균 검색량
        """
        df = self.analyze_by_time(keywords, timeframe=f'now {days}-d')

        if df.empty:
            return {}

        # 시간대별 평균 계산
        hourly_avg = {}
        for keyword in keywords:
            if keyword in df.columns:
                hourly_avg[keyword] = df.groupby('hour')[keyword].mean().to_dict()

        return hourly_avg

    def get_weekly_analysis(self, keywords):
        """
        요일별 평균 검색량 분석

        Args:
            keywords (list): 분석할 키워드

        Returns:
            dict: 요일별 평균 검색량
        """
        df = self.analyze_by_time(keywords, timeframe='today 3-m')

        if df.empty:
            return {}

        # 요일별 평균 계산
        weekly_avg = {}
        for keyword in keywords:
            if keyword in df.columns:
                weekly_avg[keyword] = df.groupby('day_of_week')[keyword].mean().to_dict()

        return weekly_avg

    def get_keyword_weights(self, timeframe='today 3-m'):
        """
        모든 키워드의 검색량 기반 가중치 계산
        워드클라우드 생성에 사용

        Args:
            timeframe (str): 분석 기간

        Returns:
            dict: {키워드: 가중치} 형태의 딕셔너리
        """
        keyword_weights = {}

        # 카테고리별로 처리
        for category, keywords in PRODUCT_KEYWORDS.items():
            # 5개씩 묶어서 처리 (API 제한)
            for i in range(0, len(keywords), 5):
                batch = keywords[i:i+5]
                df = self.fetch_trends_data(batch, timeframe=timeframe)

                if not df.empty:
                    for keyword in batch:
                        if keyword in df.columns:
                            # 평균 검색량을 가중치로 사용
                            keyword_weights[keyword] = max(df[keyword].mean(), 1)
                        else:
                            keyword_weights[keyword] = 1
                else:
                    # 데이터가 없으면 기본값 1
                    for keyword in batch:
                        keyword_weights[keyword] = 1

        return keyword_weights

    def get_top_keywords(self, n=20, timeframe='today 3-m'):
        """
        상위 N개 인기 키워드 추출

        Args:
            n (int): 추출할 키워드 개수
            timeframe (str): 분석 기간

        Returns:
            list: (키워드, 점수) 튜플 리스트
        """
        weights = self.get_keyword_weights(timeframe)

        # 점수 기준으로 정렬
        sorted_keywords = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        return sorted_keywords[:n]
