"""
워드클라우드 생성 웹 애플리케이션
텍스트 입력 또는 파일 업로드를 통해 워드클라우드 이미지를 생성합니다.
Google Trends 데이터 기반 보험 키워드 분석 기능 포함
"""

from flask import Flask, render_template, request, send_file, jsonify
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')  # GUI 없는 백엔드 사용 (macOS 스레드 문제 해결)
import matplotlib.pyplot as plt
import io
import os
from PIL import Image
import numpy as np
from trends_analyzer import TrendsAnalyzer
from keywords_config import PRODUCT_KEYWORDS, PRODUCT_CATEGORIES

app = Flask(__name__)
# 업로드 파일 크기 제한 (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# TrendsAnalyzer 인스턴스 생성
trends_analyzer = TrendsAnalyzer()

@app.route('/')
def index():
    """메인 페이지 - 통합 대시보드"""
    return render_template('dashboard.html', categories=PRODUCT_CATEGORIES)

@app.route('/generate', methods=['POST'])
def generate_wordcloud():
    """
    워드클라우드 이미지 생성 엔드포인트

    POST 파라미터:
        text (str): 워드클라우드로 만들 텍스트
        file (file): 텍스트 파일 (선택사항)

    Returns:
        PNG 이미지 파일 또는 에러 메시지
    """
    try:
        # 폼에서 텍스트 입력 받기
        text = request.form.get('text', '')

        # 파일이 업로드된 경우 파일에서 텍스트 읽기
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                text = file.read().decode('utf-8')

        # 텍스트가 비어있는지 검증
        if not text or text.strip() == '':
            return "텍스트를 입력하거나 파일을 업로드해주세요.", 400

        # 워드클라우드 객체 생성 및 설정
        wordcloud = WordCloud(
            width=800,              # 이미지 너비
            height=400,             # 이미지 높이
            background_color='white',  # 배경색
            font_path='/System/Library/Fonts/AppleSDGothicNeo.ttc',  # 한글 폰트 경로
            colormap='viridis',     # 색상 테마
            relative_scaling=0.5,   # 단어 빈도에 따른 크기 조절
            min_font_size=10        # 최소 폰트 크기
        ).generate(text)

        # matplotlib을 이용한 이미지 생성
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')  # 축 숨기기
        plt.tight_layout(pad=0)  # 여백 최소화

        # 이미지를 메모리 버퍼에 저장 (디스크에 저장하지 않음)
        img_io = io.BytesIO()
        plt.savefig(img_io, format='PNG', bbox_inches='tight', dpi=150)
        img_io.seek(0)  # 버퍼 포인터를 처음으로 이동
        plt.close()  # 메모리 해제

        # PNG 이미지 파일로 응답
        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}", 500

# /trends 라우트 제거 - 메인 페이지로 통합됨

@app.route('/api/trends/categories', methods=['GET'])
def get_category_trends():
    """
    카테고리별 검색 트렌드 데이터 API

    Query 파라미터:
        timeframe (str): 분석 기간 (기본값: 'today 3-m')
        category (str): 특정 카테고리 선택 시 하위 키워드 분석

    Returns:
        JSON: {키워드: 평균검색량} 형태
    """
    try:
        timeframe = request.args.get('timeframe', 'today 3-m')
        category = request.args.get('category', None)

        # 특정 카테고리 선택 시 하위 키워드 분석
        if category and category in PRODUCT_KEYWORDS:
            keywords = PRODUCT_KEYWORDS[category]
            keyword_scores = {}

            # 키워드를 5개씩 묶어서 처리
            for i in range(0, len(keywords), 5):
                batch = keywords[i:i+5]
                df = trends_analyzer.fetch_trends_data(batch, timeframe=timeframe)

                if not df.empty:
                    for keyword in batch:
                        if keyword in df.columns:
                            keyword_scores[keyword] = max(df[keyword].mean(), 0)
                        else:
                            keyword_scores[keyword] = 0
                else:
                    for keyword in batch:
                        keyword_scores[keyword] = 0

            return jsonify(keyword_scores)
        else:
            # 전체 보험: 카테고리별 비교
            category_scores = trends_analyzer.analyze_by_category(timeframe)
            return jsonify(category_scores)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trends/wordcloud', methods=['GET'])
def generate_trends_wordcloud():
    """
    Google Trends 데이터 기반 워드클라우드 이미지 생성

    Query 파라미터:
        timeframe (str): 분석 기간 (기본값: 'today 3-m')
        category (str): 특정 카테고리만 분석 (선택사항)

    Returns:
        PNG 이미지 파일
    """
    try:
        timeframe = request.args.get('timeframe', 'today 3-m')
        category = request.args.get('category', None)

        # 키워드 가중치 계산
        keyword_weights = trends_analyzer.get_keyword_weights(timeframe)

        # 특정 카테고리만 필터링
        if category and category in PRODUCT_KEYWORDS:
            keywords = PRODUCT_KEYWORDS[category]
            keyword_weights = {k: v for k, v in keyword_weights.items() if k in keywords}

        # 가중치가 없으면 에러 반환
        if not keyword_weights:
            return "검색 트렌드 데이터를 가져올 수 없습니다.", 400

        # 워드클라우드 생성 (빈도수 기반)
        wordcloud = WordCloud(
            width=1200,             # 이미지 너비
            height=600,             # 이미지 높이
            background_color='white',  # 배경색
            font_path='/System/Library/Fonts/AppleSDGothicNeo.ttc',  # 한글 폰트
            colormap='viridis',     # 색상 테마
            relative_scaling=0.5,   # 빈도에 따른 크기 조절
            min_font_size=10,       # 최소 폰트 크기
            max_words=100           # 최대 단어 수
        ).generate_from_frequencies(keyword_weights)

        # 이미지 생성
        plt.figure(figsize=(12, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)

        # 메모리에 저장
        img_io = io.BytesIO()
        plt.savefig(img_io, format='PNG', bbox_inches='tight', dpi=150)
        img_io.seek(0)
        plt.close()

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}", 500

@app.route('/api/trends/hourly', methods=['GET'])
def get_hourly_trends():
    """
    시간대별 검색 트렌드 분석 API

    Query 파라미터:
        keywords (str): 쉼표로 구분된 키워드 리스트
        days (int): 분석할 일수 (기본값: 7)

    Returns:
        JSON: 시간대별 평균 검색량
    """
    try:
        keywords_str = request.args.get('keywords', '')
        days = int(request.args.get('days', 7))

        if not keywords_str:
            return jsonify({"error": "keywords 파라미터가 필요합니다."}), 400

        keywords = [k.strip() for k in keywords_str.split(',')]
        hourly_data = trends_analyzer.get_hourly_analysis(keywords, days)

        return jsonify(hourly_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trends/weekly', methods=['GET'])
def get_weekly_trends():
    """
    요일별 검색 트렌드 분석 API

    Query 파라미터:
        keywords (str): 쉼표로 구분된 키워드 리스트

    Returns:
        JSON: 요일별 평균 검색량
    """
    try:
        keywords_str = request.args.get('keywords', '')

        if not keywords_str:
            return jsonify({"error": "keywords 파라미터가 필요합니다."}), 400

        keywords = [k.strip() for k in keywords_str.split(',')]
        weekly_data = trends_analyzer.get_weekly_analysis(keywords)

        return jsonify(weekly_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trends/top-keywords', methods=['GET'])
def get_top_keywords():
    """
    상위 인기 키워드 API (개별 키워드 실제 검색량 기반)

    Query 파라미터:
        n (int): 가져올 키워드 개수 (기본값: 20)
        timeframe (str): 분석 기간 (기본값: 'today 3-m')
        category (str): 특정 카테고리로 필터링 (선택사항)

    Returns:
        JSON: [[키워드, 점수], ...] 형태의 리스트
    """
    try:
        n = int(request.args.get('n', 20))
        timeframe = request.args.get('timeframe', 'today 3-m')
        category = request.args.get('category', None)

        # 상세 키워드 가중치 가져오기 (실제 개별 검색량)
        keyword_weights = trends_analyzer.get_detailed_keyword_weights(timeframe, category)

        # 점수 기준으로 정렬하여 상위 N개 추출
        sorted_keywords = sorted(keyword_weights.items(), key=lambda x: x[1], reverse=True)[:n]

        return jsonify(sorted_keywords)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vercel serverless function을 위한 export
app_handler = app

if __name__ == '__main__':
    # 개발 서버 실행 (포트 5001 사용 - macOS AirPlay가 5000 사용)
    app.run(debug=True, host='0.0.0.0', port=5001)
