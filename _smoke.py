import io, sys, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

html = urllib.request.urlopen('http://127.0.0.1:8765/').read().decode()
print('Brand area in HTML:')
i = html.find('navbar-brand')
print(html[i:i + 350])
print()
print('Total Genie occurrences:', html.count('Genie'))
print('Total TravelBot occurrences:', html.count('TravelBot'))
