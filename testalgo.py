from dhanhq import dhanhq

CLIENT_ID = "1100734437"            # your dhanClientId
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY2NDk2NzgzLCJpYXQiOjE3NjY0MTAzODMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwNzM0NDM3In0.WW15wIryjdQQ8sWkfDRPAdroyr3AgKQ-F5d3w2VWXIxNW98NRlJvDMayilZWY6mL6CrVGsqPsh2Rg8HJ550HjQ"  # same token you used for funds

dhan = dhanhq(client_id=CLIENT_ID, access_token=ACCESS_TOKEN)

# 1) Portfolio / holdings
portfolio = dhan.get_holdings()
print(portfolio)

# Optional: pretty-print each holding
if portfolio.get("status") == "success":
    for h in portfolio["data"]:
        print(
            h["securityId"],
            h["tradingSymbol"],
            "qty:", h["netQty"],
            "avg price:", h["avgPrice"],
        )
else:
    print("Error:", portfolio)
