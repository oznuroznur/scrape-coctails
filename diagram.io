Table users {
  id uuid [pk]
  name text
  email text [unique]
  phone_number text [unique]
  is_verified boolean
  avatar_url text
  created_at timestamp
}

Table cocktails {
  id serial [pk]
  name text
  image_url text
  video_url text
  description text
  glass_type_id integer [ref: > glass_types.id]
  method text
  garnish text
  difficulty text
  prep_time integer
  nutrition_info text
  is_alcoholic boolean
  servings int
  alcohol_percentage float
  calories_per_serving int
  created_at timestamp
}

Table ingredients {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  name text
  amount numeric
  unit_id integer [ref: > units.id]
}

Table glass_types {
  id serial [pk]
  name text
  image_url text
}

Table instructions {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  step_number int
  text text
}

Table allergens {
  id serial [pk]
  name text [unique]
}

Table cocktail_allergens {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  allergen_id integer [ref: > allergens.id]

  indexes {
    (cocktail_id, allergen_id) [unique]
  }
}

Table categories {
  id serial [pk]
  name text [unique]
}

Table cocktail_categories {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  category_id integer [ref: > categories.id]

  indexes {
    (cocktail_id, category_id) [unique]
  }
}

Table units {
  id serial [pk]
  name text
  description text
}

Table comments {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  user_id uuid [ref: > users.id]
  comment text
  rating int [note: "1 to 5"]
  created_at timestamp
}

Table comment_likes {
  id serial [pk]
  user_id uuid [ref: > users.id]
  comment_id integer [ref: > comments.id]
  is_liked boolean
  created_at timestamp

  indexes {
    (user_id, comment_id) [unique]
  }
}

Table favorites {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  user_id uuid [ref: > users.id]
  created_at timestamp

  indexes {
    (user_id, cocktail_id) [unique]
  }
}

Table shopping_list_items {
  id serial [pk]
  user_id uuid [ref: > users.id]
  ingredient_name text
  amount numeric
  unit_id integer [ref: > units.id]
  is_checked boolean [default: false]
  created_at timestamp
}

Table pantry_items {
  id serial [pk]
  user_id uuid [ref: > users.id]
  ingredient_name text
  amount numeric
  unit_id integer [ref: > units.id]
  expires_at date
  created_at timestamp
}

Table tags {
  id serial [pk]
  name text [unique]
}

Table cocktail_tags {
  id serial [pk]
  cocktail_id integer [ref: > cocktails.id]
  tag_id integer [ref: > tags.id]

  indexes {
    (cocktail_id, tag_id) [unique]
  }
}

