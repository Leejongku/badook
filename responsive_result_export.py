import os
import glob
import pandas as pd
import json
from datetime import datetime
import shutil
from pathlib import Path

def create_excel_report(test_results_dir="test_results"):
    """테스트 결과를 엑셀 파일로 저장합니다."""
    # 결과 폴더 확인
    if not os.path.exists(test_results_dir):
        print(f"⚠️ {test_results_dir} 폴더가 없습니다.")
        return None, None
    
    # 결과 파일 찾기 (가장 최신 파일)
    result_files = glob.glob(os.path.join(test_results_dir, "selenium_test_*.txt"))
    if not result_files:
        print("⚠️ 테스트 결과 파일을 찾을 수 없습니다.")
        return None, None
    
    # 가장 최신 파일 선택
    latest_file = max(result_files, key=os.path.getctime)
    timestamp = os.path.basename(latest_file).split('_')[2].split('.')[0]
    
    # 스크린샷 파일 찾기
    screenshots = {}
    for device in ["Desktop", "Laptop", "Tablet", "Mobile"]:
        screenshot_path = os.path.join(test_results_dir, f"{device}_{timestamp}.png")
        if os.path.exists(screenshot_path):
            screenshots[device] = screenshot_path
            print(f"✅ 스크린샷 발견: {screenshot_path}")
    
    # 결과 파일 파싱
    results_data = []
    current_device = None
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 기기 정보 확인
            if any(device in line for device in ["Desktop", "Laptop", "Tablet", "Mobile"]) and "(" in line:
                parts = line.split('(')
                device_name = parts[0].strip()
                resolution = parts[1].replace(')', '').strip()
                width, height = resolution.split('x')
                current_device = {
                    "기기": device_name,
                    "해상도": resolution,
                    "너비": width,
                    "높이": height,
                    "테스트링크": TARGET_URL,
                    "테스트결과": "확인 중...",
                    "이미지_수": 0,
                    "깨진_이미지_수": 0,
                    "스크린샷": screenshots.get(device_name, ""),
                    "타임스탬프": timestamp
                }
                
            elif current_device and "발견된 이미지 수:" in line:
                current_device["이미지_수"] = int(line.split(':')[1].strip())
                
            elif current_device and "깨진 이미지 수:" in line:
                current_device["깨진_이미지_수"] = int(line.split(':')[1].strip())
                current_device["테스트결과"] = "실패 ❌"
                results_data.append(current_device)
                current_device = None
                
            elif current_device and "깨진 이미지 없음" in line:
                current_device["깨진_이미지_수"] = 0
                current_device["테스트결과"] = "성공 ✅"
                results_data.append(current_device)
                current_device = None
    
    # DataFrame 생성
    if not results_data:
        print("⚠️ 테스트 결과 데이터를 파싱할 수 없습니다.")
        return None, None
    
    df = pd.DataFrame(results_data)
    
    # 엑셀 파일 저장
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # 스크린샷 복사 - 엑셀 파일 저장 전에 수행
    img_dir = os.path.join(reports_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    
    # 모든 스크린샷 파일을 우선 복사
    for device_name, screenshot_path in screenshots.items():
        if os.path.exists(screenshot_path):
            target_path = os.path.join(img_dir, f"{device_name}.png")
            try:
                shutil.copy2(screenshot_path, target_path)
                print(f"✅ 이미지 복사 완료: {target_path}")
            except Exception as e:
                print(f"⚠️ 이미지 복사 실패 ({device_name}): {str(e)}")
    
    # 임시 테스트 이미지 생성 (실제 스크린샷이 없는 경우 임시 이미지로 대체)
    for device in ["Desktop", "Laptop", "Tablet", "Mobile"]:
        image_path = os.path.join(img_dir, f"{device}.png")
        if not os.path.exists(image_path):
            try:
                # 테스트용 임시 이미지 (다른 테스트 결과에서 복사)
                other_images = glob.glob(os.path.join(test_results_dir, "*.png"))
                if other_images:
                    shutil.copy2(other_images[0], image_path)
                    print(f"⚠️ 임시 이미지 생성: {image_path}")
            except Exception as e:
                print(f"⚠️ 임시 이미지 생성 실패: {str(e)}")
    
    excel_file = os.path.join(reports_dir, f"반응형테스트결과_{timestamp}.xlsx")
    
    # 엑셀 작성자
    writer = pd.ExcelWriter(excel_file, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='테스트결과')
    
    # 시트 가져오기
    workbook = writer.book
    worksheet = writer.sheets['테스트결과']
    
    # 열 너비 조정
    for idx, col in enumerate(df.columns):
        max_len = df[col].astype(str).map(len).max()
        max_len = max(max_len, len(col)) + 2
        worksheet.column_dimensions[chr(65 + idx)].width = max_len
    
    # 엑셀 저장
    writer.close()
    print(f"✅ 엑셀 보고서가 생성되었습니다: {excel_file}")
    
    # 웹 페이지 생성
    html_file = create_web_report(df, reports_dir, timestamp)
    
    return excel_file, html_file

def create_web_report(df, reports_dir, timestamp):
    """테스트 결과 웹페이지를 생성합니다."""
    # 결과 데이터를 JSON으로 변환
    results_json = df.to_json(orient="records")
    
    current_time = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
    
    # HTML 템플릿 생성 (JavaScript 템플릿 문법과 충돌을 피하기 위해 괄호 이스케이핑)
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>반응형 웹 테스트 결과</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.min.css">
    <style>
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            background-color: #f8f9fa;
            padding-top: 20px;
        }}
        .container {{
            background-color: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.05);
            max-width: 1200px;
        }}
        .card {{
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
            transition: transform 0.2s;
        }}
        .card:hover {{
            transform: translateY(-5px);
        }}
        .card-header {{
            background-color: #f8f9fa;
            font-weight: bold;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card-img-top {{
            height: 200px;
            object-fit: cover;
            cursor: pointer;
        }}
        .success {{
            color: #198754;
        }}
        .failure {{
            color: #dc3545;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.85rem;
        }}
        .modal-body img {{
            max-width: 100%;
        }}
        .header-logo {{
            height: 40px;
            margin-right: 10px;
        }}
        .badge {{
            font-size: 0.8rem;
            padding: 6px 10px;
        }}
        .nav-tabs .nav-link {{
            border-radius: 10px 10px 0 0;
        }}
        .nav-link.active {{
            font-weight: bold;
        }}
        .device-info {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .device-icon {{
            font-size: 1.5rem;
            margin-right: 10px;
        }}
        .detail-row {{
            display: flex;
            margin-bottom: 5px;
        }}
        .detail-label {{
            width: 120px;
            font-weight: 500;
            color: #6c757d;
        }}
        .img-thumbnail {{
            transition: transform 0.3s;
            cursor: pointer;
        }}
        .img-thumbnail:hover {{
            transform: scale(1.03);
        }}
        .kakao-btn {{
            background-color: #FEE500;
            color: #000000;
            border: none;
        }}
        .kakao-btn:hover {{
            background-color: #FFD700;
            color: #000000;
        }}
        .tab-content {{
            padding: 25px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-top: none;
            border-radius: 0 0 10px 10px;
        }}
        .table-custom {{
            border-radius: 8px;
            overflow: hidden;
        }}
        .table-custom thead {{
            background-color: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container mb-5">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1 class="mb-1">반응형 웹 테스트 결과</h1>
                <div class="timestamp">테스트 일시: {current_time}</div>
            </div>
            <button class="btn kakao-btn" onclick="sendReport()">
                <i class="bi bi-chat-fill me-1"></i> 카카오톡으로 공유
            </button>
        </div>
        
        <ul class="nav nav-tabs mb-3" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="summary-tab" data-bs-toggle="tab" data-bs-target="#summary" type="button" role="tab" aria-controls="summary" aria-selected="true">요약</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="details-tab" data-bs-toggle="tab" data-bs-target="#details" type="button" role="tab" aria-controls="details" aria-selected="false">상세 정보</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="table-tab" data-bs-toggle="tab" data-bs-target="#table" type="button" role="tab" aria-controls="table" aria-selected="false">테이블 보기</button>
            </li>
        </ul>
        
        <div class="tab-content" id="myTabContent">
            <!-- 요약 탭 -->
            <div class="tab-pane fade show active" id="summary" role="tabpanel" aria-labelledby="summary-tab">
                <h4 class="mb-4">테스트 결과 요약</h4>
                <div class="row" id="deviceCards">
                    <!-- 카드들은 JavaScript로 채워집니다 -->
                </div>
            </div>
            
            <!-- 상세 정보 탭 -->
            <div class="tab-pane fade" id="details" role="tabpanel" aria-labelledby="details-tab">
                <h4 class="mb-4">기기별 상세 결과</h4>
                <div class="accordion" id="deviceAccordion">
                    <!-- 아코디언 항목들은 JavaScript로 채워집니다 -->
                </div>
            </div>
            
            <!-- 테이블 보기 탭 -->
            <div class="tab-pane fade" id="table" role="tabpanel" aria-labelledby="table-tab">
                <h4 class="mb-4">테이블 형식으로 보기</h4>
                <div class="table-responsive">
                    <table class="table table-hover table-custom">
                        <thead>
                            <tr>
                                <th>기기</th>
                                <th>해상도</th>
                                <th>테스트 URL</th>
                                <th>테스트 결과</th>
                                <th>이미지 수</th>
                                <th>깨진 이미지</th>
                                <th>액션</th>
                            </tr>
                        </thead>
                        <tbody id="resultsTable">
                            <!-- 테이블 행들은 JavaScript로 채워집니다 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 스크린샷 모달 -->
    <div class="modal fade" id="screenshotModal" tabindex="-1" aria-labelledby="screenshotModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="screenshotModalLabel">스크린샷 보기</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="" id="screenshotImage" class="img-fluid" alt="스크린샷">
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript 스크립트 -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 테스트 결과 데이터
        const testData = {results_json};
        
        // 페이지 로드 시 데이터 표시
        document.addEventListener('DOMContentLoaded', function() {{
            renderCards();
            renderAccordion();
            renderTable();
        }});
        
        // 카드 렌더링 함수
        function renderCards() {{
            const cardsContainer = document.getElementById('deviceCards');
            testData.forEach((device, index) => {{
                const isSuccess = device.테스트결과.includes('성공');
                
                let deviceIcon = 'bi-display';
                if (device.기기 === 'Laptop') deviceIcon = 'bi-laptop';
                if (device.기기 === 'Tablet') deviceIcon = 'bi-tablet';
                if (device.기기 === 'Mobile') deviceIcon = 'bi-phone';
                
                cardsContainer.innerHTML += `
                    <div class="col-md-6 col-lg-3">
                        <div class="card h-100">
                            <div class="card-header">
                                <span><i class="bi ${{deviceIcon}} me-2"></i>${{device.기기}}</span>
                                <span class="badge ${{isSuccess ? 'bg-success' : 'bg-danger'}}">
                                    ${{isSuccess ? '성공' : '실패'}}
                                </span>
                            </div>
                            <img src="images/${{device.기기}}.png" class="card-img-top" 
                                 onclick="openScreenshot('images/${{device.기기}}.png', '${{device.기기}} (${{device.해상도}})')" 
                                 alt="${{device.기기}} 스크린샷">
                            <div class="card-body">
                                <h5 class="card-title">${{device.해상도}}</h5>
                                <p class="card-text">
                                    <small>발견된 이미지: ${{device.이미지_수}}개</small><br>
                                    <small>깨진 이미지: ${{device.깨진_이미지_수}}개</small>
                                </p>
                                <a href="${{device.테스트링크}}" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-link-45deg"></i> 사이트 방문
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }});
        }}
        
        // 아코디언 렌더링 함수
        function renderAccordion() {{
            const accordion = document.getElementById('deviceAccordion');
            testData.forEach((device, index) => {{
                const isSuccess = device.테스트결과.includes('성공');
                
                let deviceIcon = 'bi-display';
                if (device.기기 === 'Laptop') deviceIcon = 'bi-laptop';
                if (device.기기 === 'Tablet') deviceIcon = 'bi-tablet';
                if (device.기기 === 'Mobile') deviceIcon = 'bi-phone';
                
                accordion.innerHTML += `
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="heading${{index}}">
                            <button class="accordion-button ${{index === 0 ? '' : 'collapsed'}}" type="button" 
                                    data-bs-toggle="collapse" data-bs-target="#collapse${{index}}" 
                                    aria-expanded="${{index === 0 ? 'true' : 'false'}}" aria-controls="collapse${{index}}">
                                <i class="bi ${{deviceIcon}} me-2"></i>
                                <strong>${{device.기기}}</strong> (${{device.해상도}})
                                <span class="badge ${{isSuccess ? 'bg-success' : 'bg-danger'}} ms-3">
                                    ${{isSuccess ? '성공 ✓' : '실패 ✗'}}
                                </span>
                            </button>
                        </h2>
                        <div id="collapse${{index}}" class="accordion-collapse collapse ${{index === 0 ? 'show' : ''}}" 
                             aria-labelledby="heading${{index}}" data-bs-parent="#deviceAccordion">
                            <div class="accordion-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="detail-row">
                                            <div class="detail-label">기기:</div>
                                            <div>${{device.기기}}</div>
                                        </div>
                                        <div class="detail-row">
                                            <div class="detail-label">해상도:</div>
                                            <div>${{device.해상도}}</div>
                                        </div>
                                        <div class="detail-row">
                                            <div class="detail-label">테스트 URL:</div>
                                            <div>
                                                <a href="${{device.테스트링크}}" target="_blank">${{device.테스트링크}}</a>
                                            </div>
                                        </div>
                                        <div class="detail-row">
                                            <div class="detail-label">테스트 결과:</div>
                                            <div class="${{isSuccess ? 'success' : 'failure'}}">
                                                ${{device.테스트결과}}
                                            </div>
                                        </div>
                                        <div class="detail-row">
                                            <div class="detail-label">이미지 수:</div>
                                            <div>${{device.이미지_수}}개</div>
                                        </div>
                                        <div class="detail-row">
                                            <div class="detail-label">깨진 이미지:</div>
                                            <div>${{device.깨진_이미지_수}}개</div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <img src="images/${{device.기기}}.png" class="img-thumbnail" 
                                             onclick="openScreenshot('images/${{device.기기}}.png', '${{device.기기}} (${{device.해상도}})')" 
                                             alt="${{device.기기}} 스크린샷">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }});
        }}
        
        // 테이블 렌더링 함수
        function renderTable() {{
            const tableBody = document.getElementById('resultsTable');
            testData.forEach(device => {{
                const isSuccess = device.테스트결과.includes('성공');
                
                tableBody.innerHTML += `
                    <tr>
                        <td>${{device.기기}}</td>
                        <td>${{device.해상도}}</td>
                        <td><a href="${{device.테스트링크}}" target="_blank">사이트 링크</a></td>
                        <td><span class="badge ${{isSuccess ? 'bg-success' : 'bg-danger'}}">
                            ${{isSuccess ? '성공' : '실패'}}
                        </span></td>
                        <td>${{device.이미지_수}}</td>
                        <td>${{device.깨진_이미지_수}}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" 
                                   onclick="openScreenshot('images/${{device.기기}}.png', '${{device.기기}} (${{device.해상도}})')">
                                <i class="bi bi-image"></i> 스크린샷
                            </button>
                        </td>
                    </tr>
                `;
            }});
        }}
        
        // 스크린샷 모달 열기
        function openScreenshot(imageSrc, title) {{
            const modal = new bootstrap.Modal(document.getElementById('screenshotModal'));
            document.getElementById('screenshotModalLabel').textContent = title + ' 스크린샷';
            document.getElementById('screenshotImage').src = imageSrc;
            modal.show();
        }}
        
        // 카카오톡 공유 함수
        function sendReport() {{
            // 실제 카카오톡 공유 기능은 카카오 SDK 필요
            // 여기서는 예시로 알림만 표시
            alert('이 기능은 실제 환경에서는 카카오톡 SDK를 연동하여 구현해야 합니다.');
        }}
    </script>
</body>
</html>
    """
    
    # HTML 파일 저장
    html_file = os.path.join(reports_dir, f"index_{timestamp}.html")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 웹 페이지가 생성되었습니다: {html_file}")
    print(f"   브라우저에서 file:///{os.path.abspath(html_file)} 을 열어 확인하세요.")
    
    # 링크용 인덱스 파일도 생성
    index_html = os.path.join(reports_dir, "index.html")
    with open(index_html, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=index_{timestamp}.html">
    <title>반응형 웹 테스트 결과</title>
</head>
<body>
    <p>최신 테스트 결과로 이동 중입니다...</p>
</body>
</html>
        """)
        
    return html_file

# 상수 설정
TARGET_URL = "https://flobi.cafe24.com/index.html"

if __name__ == "__main__":
    excel_file, html_file = create_excel_report()
    if excel_file and html_file:
        print("\n✨ 작업이 완료되었습니다.")
        print(f"✅ 엑셀 파일: {os.path.abspath(excel_file)}")
        print(f"✅ 웹 페이지: file:///{os.path.abspath(html_file)}")
        print("\n카카오톡으로 해당 파일들을 고객에게 공유하세요.") 