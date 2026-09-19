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
python scripts/build_sp500_universe.py --start 2015-01-01
python scripts/download_prices.py --start 2015-01-01
python scripts/run_backtest.py --input data/prices.csv
```

입력 CSV 필수 열:

```
date,ticker,open,high,low,close,volume
```

결과는 `outputs/trades.csv`, `outputs/equity.csv`, `outputs/summary.json`에 저장됩니다.

### 생존편향 통제

`build_sp500_universe.py`는 현재 구성 종목과 과거 편입·편출 이력을 이용해
`ticker,start_date,end_date` 형태의 구간을 역산합니다. 가격 행마다 당시 실제
지수 편입 여부를 표시하고, 편출일 이후에는 신규 진입을 금지합니다.

무료 Yahoo 데이터에 남아 있지 않은 상장폐지 종목은 다운로드되지 않을 수 있습니다.
`outputs/download_report.json`의 누락 종목을 반드시 확인해야 하며, 기관 수준
검증에는 CRSP·Norgate 같은 point-in-time 유료 데이터가 필요합니다.

## 검증

```bash
pytest -q
```

GitHub Actions의 `backtest.yml`은 매주 월요일과 수동 실행 시 테스트 및 백테스트를 수행합니다. `keep-alive.yml`은 장기간 커밋이 없어 예약 워크플로가 자동 비활성화되는 것을 막기 위해 50일 이상 활동이 없을 때만 빈 커밋을 생성합니다.

> 연구용 코드이며 투자 권유가 아닙니다. 거래비용, 슬리피지, 상장폐지 편향을 포함해 검증해야 합니다.
