def get_code_snippet(language): 
    snippets={"c":"#include<stdio.h>\nint main(){return 0;}","cpp":"#include<iostream>\nint main(){return 0;}","html":"<html></html>","css":"body{}","js":"console.log('hi');"} 
    return snippets.get(language.lower(),"Not found") 
