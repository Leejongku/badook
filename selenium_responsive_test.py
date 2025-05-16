import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

# 테스트할 기기 목록 정의
DEVICES = [
    {"name": "Desktop", "width": 1920, "height": 1080},
    {"name": "Laptop", "width": 1366, "height": 768},
    {"name": "Tablet", "width": 768, "height": 1024},
    {"name": "Mobile", "width": 375, "height": 667},
]

TARGET_URL = "https://flobi.cafe24.com/index.html"

def test_responsive_images():
    # 결과 폴더 생성
    results_dir = "test_results"
    os.makedirs(results_dir, exist_ok=True)
    
    # 테스트 결과 파일
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"selenium_test_{timestamp}.txt")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 백그라운드 실행 모드
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")  # 로그 레벨 최소화
    
    # Selenium 웹 드라이버 초기화
    driver = webdriver.Chrome(options=chrome_options)
    
    print(f"🧪 {TARGET_URL} 반응형 테스트 시작")
    
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(f"반응형 이미지 테스트 결과 - {TARGET_URL}\n")
        f.write(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for device in DEVICES:
            print(f"\n📱 {device['name']} ({device['width']}x{device['height']}) 테스트 중...")
            
            try:
                # 화면 크기 설정
                driver.set_window_size(device['width'], device['height'])
                
                # 페이지 로드
                driver.get(TARGET_URL)
                time.sleep(5)  # 페이지가 완전히 로드될 때까지 기다림
                
                # 스크린샷 저장
                screenshot_path = os.path.join(results_dir, f"{device['name']}_{timestamp}.png")
                driver.save_screenshot(screenshot_path)
                
                # 모든 이미지 요소 찾기
                images = driver.find_elements(By.TAG_NAME, "img")
                
                f.write(f"\n{device['name']} ({device['width']}x{device['height']}):\n")
                f.write(f"발견된 이미지 수: {len(images)}\n")
                
                broken_images = []
                for i, img in enumerate(images):
                    try:
                        # 이미지 URL
                        img_src = img.get_attribute("src") or "소스 없음"
                        
                        # 원본 크기 (자연 크기)
                        natural_width = driver.execute_script("return arguments[0].naturalWidth", img)
                        natural_height = driver.execute_script("return arguments[0].naturalHeight", img)
                        
                        # 실제 렌더링된 크기
                        rendered_width = driver.execute_script("return arguments[0].width", img)
                        rendered_height = driver.execute_script("return arguments[0].height", img)
                        
                        # 이미지가 깨진 경우 (너비나 높이가 0인 경우)
                        if natural_width == 0 or natural_height == 0:
                            broken_images.append({
                                "src": img_src,
                                "index": i + 1,
                                "broken_type": "로드 실패"
                            })
                            continue
                        
                        # 비율 계산 (원본과 렌더링된 이미지의 비율 차이가 크면 깨졌다고 간주)
                        if natural_width > 0 and natural_height > 0 and rendered_width > 0 and rendered_height > 0:
                            original_ratio = natural_width / natural_height
                            rendered_ratio = rendered_width / rendered_height
                            
                            ratio_diff = abs(original_ratio - rendered_ratio)
                            if ratio_diff > 0.1:  # 비율 차이가 10% 이상인 경우
                                broken_images.append({
                                    "src": img_src,
                                    "index": i + 1,
                                    "original_size": f"{natural_width}x{natural_height}",
                                    "rendered_size": f"{rendered_width}x{rendered_height}",
                                    "ratio_diff": ratio_diff,
                                    "broken_type": "비율 왜곡"
                                })
                    except Exception as e:
                        broken_images.append({
                            "src": img_src if 'img_src' in locals() else "알 수 없음",
                            "index": i + 1,
                            "broken_type": f"분석 실패: {str(e)}"
                        })
                
                # 깨진 이미지 결과 기록
                if broken_images:
                    f.write(f"깨진 이미지 수: {len(broken_images)}\n")
                    for img in broken_images:
                        if img["broken_type"] == "비율 왜곡":
                            f.write(f"  이미지 #{img['index']}: {img['src']}\n")
                            f.write(f"    원본 크기: {img['original_size']}, 렌더링 크기: {img['rendered_size']}, 비율 차이: {img['ratio_diff']:.2f}\n")
                        else:
                            f.write(f"  이미지 #{img['index']}: {img['src']} ({img['broken_type']})\n")
                else:
                    f.write("깨진 이미지 없음\n")
                
                print(f"✅ {device['name']} 테스트 완료. 이미지 {len(images)}개 확인, 깨진 이미지 {len(broken_images)}개")
                
            except WebDriverException as e:
                error_msg = f"❌ 드라이버 오류 발생: {str(e)}"
                print(error_msg)
                f.write(f"{error_msg}\n")
            except Exception as e:
                error_msg = f"❌ 일반 오류 발생: {str(e)}"
                print(error_msg)
                f.write(f"{error_msg}\n")
    
    # 드라이버 종료
    driver.quit()
    
    print(f"\n✨ 테스트 완료. 결과 파일: {results_file}")
    print(f"📸 스크린샷 저장 위치: {results_dir}")

if __name__ == "__main__":
    test_responsive_images() 