from mandate import *

sk, vk = new_keypair()
m = create_mandate("agent_buyer_01", 100000, ["groceries"], ["merch_kofi"])
signed = sign_mandate(m, sk)

assert verify_mandate(signed, vk)
print("valid mandate verifies")

tampered = {**signed}
tampered["scope"] = {**signed["scope"], "max_amount_paise": 10000000}
assert not verify_mandate(tampered, vk)
print("tampered amount rejected")

tampered2 = {**signed}
tampered2["scope"] = {**signed["scope"], "categories": ["groceries", "electronics"]}
assert not verify_mandate(tampered2, vk)
print("tampered category rejected")

other_sk, other_vk = new_keypair()
assert not verify_mandate(signed, other_vk)
print("wrong key rejected")