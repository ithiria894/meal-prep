import logging
from fastapi import FastAPI

from app.db import init_db
from app.routers import food, recipe, stock, plan, shopping, store, image_import, budget

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="Meal Prep Planner",
    description="DIY HelloFresh - batch cook meal prep with freezer portion tracking",
    version="0.1.0",
)

app.include_router(food.router)
app.include_router(recipe.router)
app.include_router(stock.router)
app.include_router(plan.router)
app.include_router(shopping.router)
app.include_router(store.router)
app.include_router(image_import.router)
app.include_router(budget.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"app": "meal-prep", "version": "0.1.0"}
