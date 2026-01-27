from duckduckgo_search import DDGS
import json

def test():
    with DDGS() as ddgs:
        results = list(ddgs.text("Merck KGaA milestones", max_results=5))
        print(f"Results found: {len(results)}")
        for r in results:
            print(f"- {r.get('title')}")

if __name__ == "__main__":
    test()
