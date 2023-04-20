import random
random.seed()
nmax = 15
mmax = 15
maxval = 10000
n = random.randint(1, 15)
m = random.randint(1, 15)
#A
A = []
for i in range(n):
    A.append([])
    for j in range(m):
        A[i].append(random.random() * maxval)
#b
b = []
for i in range(n):
    b.append(random.random() * maxval)
#c
c = []
for i in range(m):
    c.append(random.random() * maxval)
#signs
signs = []
for i in range(n):
    signs.append(random.choice([-1, 0, 1]))
#limits
limits = []
for j in range(m):
    limits.append(random.choice([-1, 0, 1]))
#opt
opt = random.choice(["min", "max"])

print("A = [")
for i in range(n):
    print(A[i], end = '')
    if i != n - 1:
        print(',')
print("]")
print(f"b = {b}")
print(f"c = {c}")
print(f"signs = {signs}")
print(f"limits = {limits}")
print(f"opt = '{opt}'")
