"""Entrada local opcional.
No Vercel, a entrada usada é api/index.py.
Para rodar localmente: python app.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
