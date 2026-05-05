import os
import sys

# Proje kök dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.assembler import Assembler
from core.linker import Linker
from core.object_file import ObjectFile

def main():
    print("=== RV32I Linker Fibonacci Testi ===\n")
    
    # 1. Kaynak dosyalarını oku
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_asm_path = os.path.join(base_dir, 'assets', 'fibonacci', 'main.asm')
    math_asm_path = os.path.join(base_dir, 'assets', 'fibonacci', 'math.asm')
    
    with open(main_asm_path, 'r', encoding='utf-8') as f:
        main_source = f.read()
        
    with open(math_asm_path, 'r', encoding='utf-8') as f:
        math_source = f.read()
        
    # 2. Assemble İşlemi
    print("[1] Assemble İşlemi Başlıyor...")
    asm_main = Assembler()
    if not asm_main.assemble(main_source, prog_name="MAIN"):
        print("MAIN.asm derleme hatası:")
        print("\n".join(asm_main.errors))
        return
    
    asm_math = Assembler()
    if not asm_math.assemble(math_source, prog_name="MATH"):
        print("MATH.asm derleme hatası:")
        print("\n".join(asm_math.errors))
        return
        
    print("✓ Assemble başarılı.")
    
    # 3. ObjectFile'ları Oluştur
    print("\n[2] ObjectFile'lar Oluşturuluyor...")
    obj_main = ObjectFile.from_assembler(asm_main, "main")
    obj_math = ObjectFile.from_assembler(asm_math, "math")
    print(f"✓ {obj_main.name} ve {obj_math.name} object dosyaları oluşturuldu.")
    
    # 4. Link İşlemi
    print("\n[3] Link İşlemi Başlıyor...")
    linker = Linker(text_base=0x00000000, data_base=0x00010000)
    success = linker.link([obj_main, obj_math])
    
    if not success:
        print("Linker hatası:")
        print("\n".join(linker.errors))
        return
        
    print("✓ Link işlemi başarılı.")
    
    # 5. Çıktıları Göster
    print("\n" + "="*50)
    print("                   SONUÇLAR")
    print("="*50)
    
    print("\n[Link Map]")
    print(linker.get_link_map())
    
    print("\n[Assembly Listing]")
    print(linker.get_listing([obj_main, obj_math], [asm_main, asm_math]))
    
    print("\n[HEX Çıktısı]")
    print(linker.get_hex_output())
    
if __name__ == '__main__':
    main()
