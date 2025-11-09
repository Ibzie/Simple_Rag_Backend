# Python Basics

Python is a high-level, interpreted programming language known for its simplicity and readability. Created by Guido van Rossum and first released in 1991, Python emphasizes code readability with its notable use of significant indentation.

## Variables and Data Types

Python is dynamically typed, meaning you don't need to declare variable types explicitly. The interpreter infers the type based on the value assigned.

```python
# Numbers
integer_var = 42
float_var = 3.14
complex_var = 1 + 2j

# Strings
name = "Python"
multiline = """This is a
multiline string"""

# Boolean
is_valid = True
```

## Functions

Functions in Python are defined using the `def` keyword. They can accept parameters and return values.

```python
def greet(name):
    return f"Hello, {name}!"

def add_numbers(a, b):
    return a + b

result = add_numbers(5, 3)  # Returns 8
```

## Decorators

Decorators are a powerful feature in Python that allow you to modify the behavior of functions or classes. A decorator is a function that takes another function and extends its behavior without explicitly modifying it.

```python
def uppercase_decorator(func):
    def wrapper():
        result = func()
        return result.upper()
    return wrapper

@uppercase_decorator
def greet():
    return "hello world"

print(greet())  # Outputs: HELLO WORLD
```

Common use cases for decorators include logging, authentication, caching, and timing function execution.

## List Comprehensions

List comprehensions provide a concise way to create lists. They are more readable and often faster than traditional for loops.

```python
# Traditional approach
squares = []
for i in range(10):
    squares.append(i**2)

# List comprehension
squares = [i**2 for i in range(10)]

# With condition
even_squares = [i**2 for i in range(10) if i % 2 == 0]
```

## Classes and Objects

Python supports object-oriented programming through classes. Classes encapsulate data and functions that operate on that data.

```python
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name} says woof!"

    def get_age_in_dog_years(self):
        return self.age * 7

my_dog = Dog("Buddy", 3)
print(my_dog.bark())  # Outputs: Buddy says woof!
```

## Modules and Imports

Python's module system allows you to organize code into reusable files. You can import built-in modules, third-party packages, or your own modules.

```python
# Importing entire module
import math
print(math.pi)

# Importing specific functions
from datetime import datetime, timedelta

# Importing with alias
import numpy as np
```

## Exception Handling

Python uses try-except blocks to handle errors gracefully.

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    print("This always executes")
```

## File Operations

Reading and writing files in Python is straightforward using the `open()` function with context managers.

```python
# Writing to a file
with open('example.txt', 'w') as f:
    f.write("Hello, World!")

# Reading from a file
with open('example.txt', 'r') as f:
    content = f.read()
    print(content)
```

## Lambda Functions

Lambda functions are small anonymous functions defined with the `lambda` keyword. They can have any number of arguments but only one expression.

```python
# Regular function
def square(x):
    return x ** 2

# Lambda equivalent
square = lambda x: x ** 2

# Lambda with multiple arguments
multiply = lambda x, y: x * y

# Lambda in higher-order functions
numbers = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x**2, numbers))
```

These basics form the foundation of Python programming and are essential for any Python developer to master.
