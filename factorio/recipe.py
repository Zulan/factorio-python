from factorio import item as item_module

class Ingredient:
    def __init__(self, amount, item):
        self.amount = amount
        self.item = item

    @classmethod
    def from_dict(cls, i, items):
        if "amount" in i:
            amount = i["amount"]
        else:
            amount = (i["amount_min"] + i["amount_max"]) / 2
        amount *= i.get("probability", 1)
        return cls(amount, item_module.get_item(items, i["name"]))

    def __repr__(self):
        return "%s(%d, %r)" % (type(self).__name__, self.amount, self.item.name)

class Recipe:
    def __init__(self, name, category, time, ingredients, products):
        self.name = name
        self.category = category
        self.time = time
        self.ingredients = ingredients
        self.products = products
        for product in self.products:
            product.item.add_recipe(self)
        for ingredient in self.ingredients:
            ingredient.item.add_use(self)

    @classmethod
    def from_dict(cls, d, items):
        time = d["energy"]
        products = []
        for product in d["products"]:
            products.append(Ingredient.from_dict(product, items))
        ingredients = []
        for ingredient in d["ingredients"]:
            ingredients.append(Ingredient.from_dict(ingredient, items))
        return cls(d["name"], d["category"], time, ingredients, products)

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.name)

    def gives(self, item):
        for product in self.products:
            if product.item == item:
                return product.amount

    def makes_resource(self):
        return False

class ResourceRecipe(Recipe):
    def __init__(self, item):
        super().__init__(item.name, None, 0, [], [Ingredient(1, item)])

    def makes_resource(self):
        return True

class MiningRecipe(Recipe):
    """Pseudo-recipe representing resource extraction."""
    def __init__(self, item, category, hardness, mining_time, ingredients=None):
        self.hardness = hardness
        self.mining_time = mining_time
        if ingredients is None:
            ingredients = []
        super().__init__(item.name, category, 0, ingredients, [Ingredient(1, item)])

    def makes_resource(self):
        return True

def ignore_recipe(d):
    """Excise the barrel-emptying recipes from the graph."""
    return d["subgroup"] == "empty-barrel"

def get_recipe_graph(data):
    recipes = {}
    items = item_module.get_items(data)
    for recipe in data["recipes"].values():
        if ignore_recipe(recipe):
            continue
        r = Recipe.from_dict(recipe, items)
        recipes[r.name] = r
    for entity in data["entities"].values():
        category = entity.get("resource_category")
        if not category:
            continue
        if category == "basic-solid":
            name = entity["name"]
            props = entity["mineable_properties"]
            item = items[name]
            ingredients = None
            if "required_fluid" in props:
                ingredients = [Ingredient(props["fluid_amount"]//10, items[props["required_fluid"]])]
            recipes[name] = MiningRecipe(
                    item,
                    "mining-" + category,
                    props["hardness"],
                    props["mining_time"],
                    ingredients,
            )
    for item in items.values():
        if len(item.recipes) == 0:
            r = ResourceRecipe(item)
            recipes[r.name] = r
    return items, recipes
