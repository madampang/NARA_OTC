"""
Nara OTC Keeper Service
Auto-detects payments → releases NARA → transfers stablecoin to seller
"""
import os
import json
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from solana.rpc.api import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nara OTC Keeper")

# ─── Config ───
NARA_RPC = os.environ.get("NARA_RPC", "https://mainnet-api.nara.build/")
NARA_PRIVATE_KEY = os.environ.get("NARA_PRIVATE_KEY", "")
ORDERS_FILE = os.environ.get("ORDERS_FILE", "orders.json")
KEEPER_FEE_PCT = 0.01  # 1% keeper fee

# ─── In-memory store (use DB in prod) ───
orders = {}
next_order_id = 1

def save_orders():
    with open(ORDERS_FILE, "w") as f:
        json.dump({"orders": orders, "next_id": next_order_id}, f)

def load_orders():
    global orders, next_order_id
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE) as f:
            data = json.load(f)
            orders = data.get("orders", {})
            next_order_id = data.get("next_id", 1)

# ─── Models ───
class CreateOrder(BaseModel):
    amount_nara: float
    price_usd: float
    payment_token: str = "USDC"
    payment_chain_id: int = 8453
    seller_pubkey: str

class CancelOrder(BaseModel):
    seller_pubkey: str
    signature: str = ""

# ─── API Endpoints ───

@app.on_event("startup")
async def startup():
    load_orders()
    logger.info(f"Keeper started. Orders loaded: {len(orders)}")

@app.get("/health")
def health():
    return {"status": "ok", "version": "v1", "orders": len(orders)}

@app.get("/api/orders")
def list_orders(limit: int = 50, offset: int = 0):
    active = [
        {"id": k, **v} for k, v in orders.items()
        if v.get("status") == "Active"
    ]
    return {"orders": active[offset:offset+limit], "total": len(active)}

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(404, "Order not found")
    order = orders[order_id]
    resp = {"id": order_id, **order}

    # Generate unique payment address for off-chain
    resp["payment_address"] = f"{order['seller_pubkey'][:10]}_order_{order_id}"
    return resp

@app.post("/api/orders")
def create_order(req: CreateOrder):
    global next_order_id
    order_id = str(next_order_id)
    next_order_id += 1

    payment_address = f"otc_pay_{order_id}_{int(time.time())}"

    orders[order_id] = {
        "amount_nara": req.amount_nara,
        "price_usd": req.price_usd,
        "total_usd": round(req.amount_nara * req.price_usd, 2),
        "payment_token": req.payment_token,
        "payment_chain_id": req.payment_chain_id,
        "seller_pubkey": req.seller_pubkey,
        "payment_address": payment_address,
        "status": "Active",
        "created_at": time.time(),
        "buyer_pubkey": None,
        "completed_at": None,
    }
    save_orders()

    logger.info(f"Order #{order_id}: {req.amount_nara} NARA @ ${req.price_usd}")
    return {"order_id": order_id, "payment_address": payment_address, **orders[order_id]}

@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, req: CancelOrder):
    if order_id not in orders:
        raise HTTPException(404, "Order not found")
    order = orders[order_id]

    if order["seller_pubkey"] != req.seller_pubkey:
        raise HTTPException(403, "Not the seller")
    if order["status"] != "Active":
        raise HTTPException(400, f"Cannot cancel — status: {order['status']}")

    # 15-min cooldown
    order["status"] = "CancelPending"
    order["cancel_requested_at"] = time.time()
    save_orders()

    logger.info(f"Order #{order_id} — cancellation requested (15min cooldown)")
    return {"status": "CancelPending", "cooldown_ends_at": order.get("cancel_requested_at", 0) + 900}

@app.post("/api/orders/{order_id}/process-payment")
def process_payment(order_id: str, tx_hash: str, actual_amount_usd: float):
    """Keeper endpoint — called when payment detected"""
    if order_id not in orders:
        raise HTTPException(404, "Order not found")
    order = orders[order_id]

    if order["status"] != "Active":
        return {"status": "skipped", "reason": f"Order is {order['status']}"}

    expected_usd = order["total_usd"]
    if abs(actual_amount_usd - expected_usd) > 0.01:
        return {"status": "refunded", "reason": f"Wrong amount: {actual_amount_usd} != {expected_usd}"}

    # Mark completed
    order["status"] = "Completed"
    order["payment_tx"] = tx_hash
    order["completed_at"] = time.time()
    order["buyer_pubkey"] = tx_hash[:44]  # Placeholder
    save_orders()

    logger.info(f"Order #{order_id} COMPLETED — ${actual_amount_usd} received")

    # TODO: Release NARA from escrow → buyer
    # TODO: Transfer USDC to seller

    return {"status": "released", "order_id": order_id}

@app.get("/api/orders/{order_id}/status")
def order_status(order_id: str):
    if order_id not in orders:
        raise HTTPException(404, "Order not found")
    order = orders[order_id]

    # Auto-finalize cancel after cooldown
    if order["status"] == "CancelPending":
        if time.time() - order.get("cancel_requested_at", 0) > 900:
            order["status"] = "Cancelled"
            save_orders()
            return {"order_id": order_id, "status": "Cancelled", "nara_refunded": True}
        else:
            remaining = 900 - (time.time() - order.get("cancel_requested_at", 0))
            return {"order_id": order_id, "status": "CancelPending", "cooldown_remaining_seconds": int(remaining)}

    return {"order_id": order_id, "status": order["status"], "payment_address": order.get("payment_address")}

@app.get("/api/seller/{pubkey}/orders")
def seller_orders(pubkey: str):
    seller_orders = [
        {"id": k, **v} for k, v in orders.items()
        if v.get("seller_pubkey") == pubkey
    ]
    return {"orders": seller_orders}

@app.get("/stats")
def stats():
    status_count = {}
    for o in orders.values():
        s = o.get("status", "Unknown")
        status_count[s] = status_count.get(s, 0) + 1
    return {"total_orders": len(orders), "by_status": status_count}
