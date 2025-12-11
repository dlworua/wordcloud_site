"""
워드클라우드 생성 웹 애플리케이션
텍스트 입력 또는 파일 업로드를 통해 워드클라우드 이미지를 생성합니다.
"""

from flask import Flask, render_template, request, send_file
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import os
from PIL import Image
import numpy as np

app = Flask(__name__)
# 업로드 파일 크기 제한 (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

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

if __name__ == '__main__':
    # 개발 서버 실행
    app.run(debug=True, host='0.0.0.0', port=5000)
