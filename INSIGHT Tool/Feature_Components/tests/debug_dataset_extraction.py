import re

def detect_language(file_path):
    if file_path.endswith('.py'):
        return 'python'
    elif file_path.endswith('.java'):
        return 'java'
    return 'unknown'

def extract_entities(context, language, classes_set, functions_set):
    """Extract class and function names from diff hunk context"""
    if not context:
        return
    
    print(f"  Scanning Context: '{context}'")
    
    if language == 'python':
        # Extract class names: class ClassName or class ClassName(Base)
        class_match = re.search(r'class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            print(f"    Found Class: {class_match.group(1)}")
            classes_set.add(class_match.group(1))
            return 
        
        # Extract function/method names: def function_name
        func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', context)
        if func_match:
            print(f"    Found Function: {func_match.group(1)}")
            functions_set.add(func_match.group(1))
    
    elif language == 'java':
        class_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:abstract)?\s*class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            classes_set.add(class_match.group(1))
            return

        method_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:\w+(?:<[^>]+>)?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', context)
        if method_match:
            method_name = method_match.group(1)
            if method_name not in ['class', 'interface', 'enum', 'extends', 'implements', 'throws']:
                functions_set.add(method_name)

def parse_diff(diff_text):
    changed_files = set()
    changed_classes = set()
    changed_functions = set()
    
    lines = diff_text.split('\n')
    current_file = None
    current_language = None
    
    hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@\s*(.*)')
    
    for line in lines:
        if line.startswith('diff --git'):
            match = re.search(r'b/(.+)$', line)
            if match:
                current_file = match.group(1)
                changed_files.add(current_file)
                current_language = detect_language(current_file)
            continue
        
        if line.startswith('+++') and line.startswith('+++ b/'):
            file_path = line[6:].strip()
            if file_path:
                changed_files.add(file_path)
                current_file = file_path
                current_language = detect_language(current_file)
            continue
        
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            context = hunk_match.group(2)
            extract_entities(context, current_language, changed_classes, changed_functions)
            continue
            
    return list(changed_files), list(changed_classes), list(changed_functions)

def run_tests():
    # Test 1: Modifying __init__
    print("\n--- Test 1: Modifying __init__ ---")
    diff1 = """diff --git a/test.py b/test.py
index abc..def 100644
--- a/test.py
+++ b/test.py
@@ -10,7 +10,7 @@ class Test:
     def __init__(self):
-        self.x = 1
+        self.x = 2
"""
    # Note: In reality, git diff context often puts the function def in the @@ line
    diff1_real = """diff --git a/test.py b/test.py
@@ -10,7 +10,7 @@ def __init__(self):
-        self.x = 1
+        self.x = 2
"""
    
    f, c, func = parse_diff(diff1_real)
    print(f"Extracted: Files={f}, Classes={c}, Funcs={func}")

    # Test 2: Adding a NEW function (Header is NOT the function)
    print("\n--- Test 2: Adding New Function ---")
    diff2 = """diff --git a/test.py b/test.py
@@ -50,0 +51,3 @@ def existing_func():
     pass
 
+def new_func():
+    print("New")
"""
    f, c, func = parse_diff(diff2)
    print(f"Extracted: Files={f}, Classes={c}, Funcs={func}")
    
    # Test 3: Modifying __init__ but header is class
    print("\n--- Test 3: Header is Class, change is inside __init__ (missed header) ---")
    diff3 = """diff --git a/test.py b/test.py
@@ -10,5 +10,5 @@ class MyClass:
     def __init__(self):
-        self.x = 1
+        self.x = 2
"""
    # Here the Hunk Header context is likely "class MyClass:" if the lines are close?
    # Actually, git usually picks the closest enclosing, which should be __init__ if close.
    # But let's assume the header text provided is "class MyClass:"
    
    diff3_simulated = """diff --git a/test.py b/test.py
@@ -10,5 +10,5 @@ class MyClass:
     def __init__(self):
-        self.x = 1
+        self.x = 2
"""
    f, c, func = parse_diff(diff3_simulated)
    print(f"Extracted: Files={f}, Classes={c}, Funcs={func}")

if __name__ == "__main__":
    run_tests()
