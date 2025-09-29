import re

def find_duplicate_routes():
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        routes = []
        functions = []
        
        for i, line in enumerate(lines, 1):
            # Buscar @app.route
            if '@app.route' in line:
                route_match = re.search(r"@app\.route\(['\"]([^'\"]+)['\"]", line)
                if route_match:
                    route_path = route_match.group(1)
                    routes.append((i, route_path, line.strip()))
            
            # Buscar definiciones de funciones después de @app.route
            if line.strip().startswith('def ') and i > 1:
                # Verificar si la línea anterior era @app.route o @login_required
                prev_lines = [lines[j].strip() for j in range(max(0, i-3), i-1)]
                if any('@app.route' in prev or '@login_required' in prev for prev in prev_lines):
                    func_match = re.search(r'def\s+(\w+)', line)
                    if func_match:
                        func_name = func_match.group(1)
                        functions.append((i, func_name, line.strip()))
        
        print("RUTAS ENCONTRADAS:")
        route_counts = {}
        for line_num, route, code in routes:
            print(f"  Línea {line_num}: {route}")
            route_counts[route] = route_counts.get(route, 0) + 1
        
        print("\nFUNCIONES ENCONTRADAS:")
        func_counts = {}
        for line_num, func, code in functions:
            print(f"  Línea {line_num}: {func}()")
            func_counts[func] = func_counts.get(func, 0) + 1
        
        print("\nDUPLICADOS ENCONTRADOS:")
        duplicates_found = False
        
        for route, count in route_counts.items():
            if count > 1:
                print(f"  ❌ RUTA '{route}' aparece {count} veces")
                duplicates_found = True
        
        for func, count in func_counts.items():
            if count > 1:
                print(f"  ❌ FUNCIÓN '{func}()' aparece {count} veces")
                duplicates_found = True
                
                # Mostrar líneas específicas
                print(f"     Líneas donde aparece '{func}':")
                for line_num, f_name, code in functions:
                    if f_name == func:
                        print(f"       Línea {line_num}: {code}")
        
        if not duplicates_found:
            print("  ✅ No se encontraron duplicados")
        
        # Mostrar contexto alrededor de la línea 645
        print(f"\nCONTEXTO ALREDEDOR DE LA LÍNEA 645:")
        start = max(0, 645 - 5)
        end = min(len(lines), 645 + 5)
        for i in range(start, end):
            marker = " ➤ " if i + 1 == 645 else "   "
            print(f"{marker}Línea {i+1}: {lines[i].rstrip()}")
            
    except FileNotFoundError:
        print("❌ No se encontró app.py en el directorio actual")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    find_duplicate_routes()