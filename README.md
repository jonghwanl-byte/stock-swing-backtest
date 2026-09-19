# Stock Swing Backtest

미국 주식을 **최대 3개월(63거래일)** 보유하는 규칙 기반 스윙 전략의 연구용 저장소입니다.

핵심 원칙은 뉴스의 문장을 주관적으로 해석하지 않고, 이미 가격·거래량에 나타난 반응을 수치화하는 것입니다.

## 현재 전략

- 유동성: 20일 평균 거래대금이 기준 이상
- 추세: 종가 > 50일 이동평균 > 200일 이동평균
- 상대 모멘텀: 63일·126일 수익률
- 촉매 대용치: 갭 상승률과 20일 평균 대비 거래량 급증
- 진입: 매주 금요일 종합점수 상위 종목
- 청산: 최대 63거래일, 손절, 추적손절 또는 추세 훼손

모든 기준값은 `config/strategy.yml`에서 변경할 수 있습니다.

## 실행

```bash
python -m pip install -r requirements.txt
python scripts/run_backtest.py --input data/prices.csv --download-report outputs/download_report.json
```

입력 CSV 필수 열:

```
date,ticker,open,high,low,close,volume
```

결과는 `outputs/trades.csv`, `outputs/equity.csv`, `outputs/annual_metrics.csv`, `outputs/summary.json`에 저장됩니다. `summary.json`에는 CAGR, 연환산 변동성, 샤프, 최대낙폭, 승률이 포함됩니다. `--benchmark`를 지정하면 벤치마크 누적수익률과 초과수익도 함께 계산합니다.

## 검증

```bash
pytest -q
```

GitHub Actions의 `backtest.yml`은 매주 월요일과 수동 실행 시 테스트 및 백테스트를 수행합니다. `keep-alive.yml`은 장기간 커밋이 없어 예약 워크플로가 자동 비활성화되는 것을 막기 위해 50일 이상 활동이 없을 때만 빈 커밋을 생성합니다.

> 연구용 코드이며 투자 권유가 아닙니다. 거래비용, 슬리피지, 상장폐지 편향을 포함해 검증해야 합니다.
