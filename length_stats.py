import csv, os, statistics

path = os.path.expanduser("~/hf/swiss-sme-bookkeeping-dataset/swiss_sme_bookkeeping_synthetic.csv")
lens = sorted(len(r["text"]) for r in csv.DictReader(open(path, encoding="utf-8")))
n = len(lens)
print("rows", n, "median", statistics.median(lens), "max", max(lens))
print("99th percentile", lens[int(n * 0.99) - 1])
