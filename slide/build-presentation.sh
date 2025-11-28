#!/bin/bash

# Istio Session 프레젠테이션 빌드 스크립트

set -e

echo "🚀 Istio Session 프레젠테이션 빌드 시작..."

# Marp CLI 설치 확인
if ! command -v marp &> /dev/null; then
    echo "📦 Marp CLI 설치 중..."
    npm install -g @marp-team/marp-cli
fi

# HTML 생성 (Mermaid 자동 렌더링)
echo "🌐 HTML 생성 중..."
marp istio-session.md -o istio-session.html --html

# PDF 생성 (선택)
echo "📄 PDF 생성 중..."
marp istio-session.md -o istio-session.pdf --allow-local-files --pdf

# PowerPoint 생성 (선택)
# echo "📊 PPTX 생성 중..."
# marp istio-session.md -o istio-session.pptx

echo "✅ 빌드 완료!"
echo ""
echo "생성된 파일:"
echo "  - istio-session.html"
echo "  - istio-session.pdf"
echo ""
echo "HTML 파일을 브라우저에서 열어서 확인하세요:"
echo "  open istio-session.html"
