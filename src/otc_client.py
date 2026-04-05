"""
Nara OTC Client — Python SDK for NARA OTC trading on Solana-compatible chain
"""
import os
import time
import requests
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import base58

class OTCClient:
    def __init__(
        self,
        private_key=None,
        contract_address=None,
        nara_rpc="https://mainnet-api.nara.build/",
        keeper_url="https://naraotc.vercel.app",
    ):
        self.keypair = Keypair.from_bytes(base58.b58decode(private_key))
        self.contract_address = Pubkey.from_string(contract_address) if contract_address else None
        self.client = Client(nara_rpc)
        self.keeper_url = keeper_url.rstrip('/')
        self.token_mint = "YOUR_NARA_TOKEN_MINT"

    @property
    def pubkey(self):
        return self.keypair.pubkey()

    # ─── Buyer methods ───

    def list_active_orders(self, limit=50, offset=0):
        """Get active sell orders from Keeper"""
        resp = requests.get(f"{self.keeper_url}/api/orders", params={"limit": limit, "offset": offset})
        resp.raise_for_status()
        data = resp.json()
        return data.get("orders", []), data.get("total", 0)

    def get_order(self, order_id):
        """Get single order detail"""
        resp = requests.get(f"{self.keeper_url}/api/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()

    def buy_full(self, order_id):
        """Buy entire order — returns payment address and amount"""
        order = self.get_order(order_id)
        payment_address = order.get("payment_address")
        amount = order.get("amount_nara")
        price_usd = order.get("price_usd")

        if not payment_address:
            raise ValueError(f"Order {order_id} has no payment address. Maybe using off-chain escrow?")

        return {
            "order_id": order_id,
            "payment_address": payment_address,
            "amount_nara": amount,
            "total_usd": amount * price_usd,
            "keeper_url": f"{self.keeper_url}/api/orders/{order_id}/status",
        }

    # ─── Seller methods ───

    def create_sell_order(
        self,
        amount_nara,
        price_usd,
        payment_token="USDC",
        payment_chain_id=8453,  # Base
    ):
        """Create a new sell order"""
        resp = requests.post(
            f"{self.keeper_url}/api/orders",
            json={
                "amount_nara": amount_nara,
                "price_usd": price_usd,
                "payment_token": payment_token,
                "payment_chain_id": payment_chain_id,
                "seller_pubkey": str(self.pubkey),
                "signature": self._sign_order(amount_nara, price_usd),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("order_id"), data

    def cancel_order(self, order_id):
        """Cancel an active order"""
        resp = requests.delete(
            f"{self.keeper_url}/api/orders/{order_id}",
            json={"seller_pubkey": str(self.pubkey)},
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Balance checks ───

    def nara_balance(self):
        """Check NARA balance"""
        balance = self.client.get_balance(self.pubkey)
        return balance.value / 10**9

    def stablecoin_balance(self, chain_id=8453, token="USDC"):
        """Check stablecoin balance on specified chain"""
        return 0  # Requires cross-chain API integration

    # ─── Internal ───

    def _sign_order(self, amount_nara, price_usd):
        """Sign order data with seller's private key"""
        message = f"{amount_nara}:{price_usd}:{self.pubkey!s}:{int(time.time())}".encode()
        signature = self.keypair.sign_message(message)
        return base58.b58encode(bytes(signature)).decode()


# ─── Usage Example ───

if __name__ == "__main__":
    client = OTCClient(
        private_key=os.environ.get("NARA_PRIVATE_KEY", ""),
        contract_address=os.environ.get("OTC_CONTRACT_ADDRESS"),
    )

    print(f"Wallet: {client.pubkey!s}")
    print(f"NARA Balance: {client.nara_balance():.4f}")

    # List active orders
    orders, total = client.list_active_orders(limit=50)
    if orders:
        best = min(orders, key=lambda o: o["price_usd"])
        print(f"Best order: #{best['id']} — {best['amount_nara']} NARA @ ${best['price_usd']}")
    else:
        print("No active orders")
