import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import download_network, inspect_network

if __name__ == "__main__":
    print("=" * 55)
    print("  MotoRoute - Road Network Downloader")
    print("  Partido State University BSCS Research")
    print("=" * 55)

    force = "--force" in sys.argv
    multiple = "--multiple" in sys.argv

    if multiple:
        print("\n📦 Mode: Downloading combined network (Ocampo, Tigaon, Goa)")
        G = download_network(force_reload=force, multiple=True)
    else:
        print("\n📦 Mode: Downloading single network (Naga)")
        G = download_network(force_reload=force, multiple=False)

    print(f"\n[Done] Network ready.")
    print(f"       Nodes: {len(G.nodes)}")
    print(f"       Edges: {len(G.edges)}")

    if "--inspect" in sys.argv:
        inspect_network(G)