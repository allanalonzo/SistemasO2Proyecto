import libvirt

try:
    conn = libvirt.open("qemu:///system")
    if conn is None:
        print("❌ No se pudo conectar a libvirt.")
    else:
        print("✅ Conectado a libvirt correctamente.")
        conn.close()
except libvirt.libvirtError as e:
    print(f"❌ Error al conectar con libvirt: {e}")
