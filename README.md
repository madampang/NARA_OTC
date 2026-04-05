# 🥜 Nara OTC — NARA/USDT 场外交易指南

> Nara Chain 版本的 Axon OTC — 买卖 NARA 代币的完整操作指南。卖方挂单托管 NARA，买方直接转 USDT/USDC 到专属付款地址，Keeper 自动放 NARA。

## 核心特点

- **无需锁单**：买方直接转账即可，无需任何预操作
- **买方无需 Nara gas**：全程只需 BSC/Arb 上的 BNB/ETH
- **专属付款地址**：每笔订单有独立收款地址，不会搞混
- **全自动成交**：Keeper 检测到 USDT 到账后，自动放 NARA 给买方、自动转 USDT 给卖方
- **安全托管**：NARA 由智能合约锁定，取消需 15 分钟冷却期
- **并发安全**：多人同时付款，先到先得，后到自动退款

## 链和代币

| 链 | Chain ID | 角色 | 代币 |
|---|----------|------|------|
| Nara | - | NARA 托管链 | NARA (native) |
| BSC | 56 | 买方付款链 | USDT, USDC |
| Base | 8453 | 买方付款链 | USDC |

## 快速开始

### 安装依赖

```bash
pip install web3 solana solders requests
```

### 初始化客户端

```python
from src.otc_client import OTCClient

client = OTCClient(
    private_key=os.environ["NARA_PRIVATE_KEY"],
    otc_api_url="https://naraotc.vercel.app",
)
```

### 完整买方示例

```python
# 浏览卖单
orders, _ = client.list_active_orders(limit=50)
if not orders:
    exit("当前没有卖单")

best = min(orders, key=lambda o: o['price_usd'])
print(f"最优: #{best['id']} {best['amount_nara']} NARA @ ${best['price_usd']} "
      f"总价 {best['total_usd']:.2f} {best['payment_token']}")

# 检查余额
bal = client.stablecoin_balance(best['payment_chain_id'], best['payment_token'])
if bal < best['total_usd']:
    exit(f"余额不足: 需要 {best['total_usd']:.2f}, 持有 {bal:.2f}")

# 一键买入
result = client.buy_full(best['id'])
print(f"付款地址: {result['payment_address']}")
print(f"付款 tx: {result['payment_tx']}")
# Keeper 将自动放 NARA 到你的地址
```

### 完整卖方示例

```python
from src.otc_client import OTCClient

client = OTCClient(private_key=os.environ["NARA_PRIVATE_KEY"])

# 创建卖单
order_id, tx = client.create_sell_order(
    amount_nara=100,
    price_usd=0.05,
    payment_chain_id=56,        # BSC
    payment_token="USDT",
)
print(f"卖单 #{order_id} 已创建, 总价 {100 * 0.05:.2f} USDT")

# 取消卖单（15 分钟冷却）
client.request_cancel_order(order_id)
import time; time.sleep(900)
client.finalize_cancel_order(order_id)
```

## Keeper HTTP API

| 路径 | 说明 |
|------|------|
| `/health` | 健康检查 |
| `/api/orders` | 活跃卖单列表 |
| `/api/orders/{id}` | 单笔详情 |
| `/api/orders/{id}/buy` | 同 `/api/orders/{id}` |

```bash
curl -s "https://naraotc.vercel.app/api/orders"
curl -s "https://naraotc.vercel.app/api/orders/1"
```

## Deploy

### Frontend → Vercel
```bash
cd frontend
# Push to GitHub → Import at vercel.com → Deploy
```

### Keeper → Railway/Fly.io
```bash
cd keeper
# Deploy Python FastAPI service
```
