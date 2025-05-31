import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import libvirt
import subprocess
import os
import xml.etree.ElementTree as ET
import threading  # ✅ Importación añadida

class VirtualizationClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cliente de Virtualización - SO2 2025")
        self.geometry("900x600")
        self.minsize(800, 500)

        self.conn = None
        self.vm_data = {}
        self.selected_vm_name = None
        self.connect_libvirt()
        self.create_menu()
        self.create_main_layout()
        self.load_vms()

    def connect_libvirt(self):
        try:
            self.conn = libvirt.open("qemu:///system")
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo conectar a libvirt:\n{e}")
            self.quit()

    def create_menu(self):
        menubar = tk.Menu(self)
        archivo_menu = tk.Menu(menubar, tearoff=0)
        archivo_menu.add_command(label="Salir", command=self.quit)
        menubar.add_cascade(label="Archivo", menu=archivo_menu)

        maquina_menu = tk.Menu(menubar, tearoff=0)
        maquina_menu.add_command(label="Crear Nueva VM", command=self.create_vm_dialog)
        menubar.add_cascade(label="Máquina", menu=maquina_menu)

        ayuda_menu = tk.Menu(menubar, tearoff=0)
        ayuda_menu.add_command(label="Acerca de", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
        self.config(menu=menubar)

    def create_main_layout(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.vm_listbox = tk.Listbox(main_frame)
        self.vm_listbox.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.vm_listbox.bind("<<ListboxSelect>>", self.on_vm_select)

        details_frame = tk.Frame(main_frame)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.vm_details = tk.LabelFrame(details_frame, text="Detalles de la Máquina Virtual", padx=10, pady=10)
        self.vm_details.pack(fill=tk.BOTH, expand=True)

        self.vm_info = tk.Label(self.vm_details, text="Seleccione una VM de la lista para ver los detalles.")
        self.vm_info.pack(anchor="w")

        self.btn_frame = tk.Frame(details_frame)
        self.btn_frame.pack(pady=10)

        for label in ["Iniciar", "Detener", "Reiniciar", "Eliminar", "Ver Pantalla"]:
            btn = tk.Button(self.btn_frame, text=label, width=12, command=lambda l=label: self.vm_action(l))
            btn.pack(side=tk.LEFT, padx=5)

        create_vm_btn = tk.Button(self, text="+ Crear nueva máquina virtual", command=self.create_vm_dialog)
        create_vm_btn.pack(pady=5)

    def load_vms(self):
        self.vm_listbox.delete(0, tk.END)
        self.vm_data.clear()
        for domain_id in self.conn.listDomainsID():
            domain = self.conn.lookupByID(domain_id)
            name = domain.name()
            self.vm_data[name] = "Running"
            self.vm_listbox.insert(tk.END, f"{name} [Running]")
        for name in self.conn.listDefinedDomains():
            self.vm_data[name] = "Shutoff"
            self.vm_listbox.insert(tk.END, f"{name} [Shutoff]")

    def on_vm_select(self, event):
        selection = self.vm_listbox.curselection()
        if selection:
            line = self.vm_listbox.get(selection[0])
            self.selected_vm_name = line.split(" [")[0]
            self.update_vm_details()

    def update_vm_details(self):
        vm_name = self.selected_vm_name
        if not vm_name:
            return
        try:
            domain = self.conn.lookupByName(vm_name)
            info = domain.info()
            estado = {
                libvirt.VIR_DOMAIN_NOSTATE: "Sin estado",
                libvirt.VIR_DOMAIN_RUNNING: "En ejecución",
                libvirt.VIR_DOMAIN_BLOCKED: "Bloqueada",
                libvirt.VIR_DOMAIN_PAUSED: "Pausada",
                libvirt.VIR_DOMAIN_SHUTDOWN: "Apagándose",
                libvirt.VIR_DOMAIN_SHUTOFF: "Apagada",
                libvirt.VIR_DOMAIN_CRASHED: "Crasheada",
                libvirt.VIR_DOMAIN_PMSUSPENDED: "Suspendida"
            }.get(info[0], "Desconocido")
            ram_max = info[1] // 1024
            ram_used = info[2] // 1024
            vcpus = info[3]
            cpu_time = info[4] // 1_000_000_000
            xml_desc = domain.XMLDesc()
            root = ET.fromstring(xml_desc)
            disk_path = "Desconocido"
            for disk in root.findall(".//disk"):
                source = disk.find("source")
                if source is not None and "file" in source.attrib:
                    disk_path = source.attrib["file"]
                    break
            self.vm_info.config(text=(
                f"Nombre: {vm_name}\n"
                f"Estado: {estado}\n"
                f"RAM: {ram_used} / {ram_max} MB\n"
                f"CPUs: {vcpus}\n"
                f"CPU Time: {cpu_time} s\n"
                f"Disco: {disk_path}"
            ))
        except libvirt.libvirtError as e:
            self.vm_info.config(text=f"Error al obtener detalles:\n{e}")
        self.after(1000, self.update_vm_details)

    def abrir_virt_viewer(self, vm_name):  # ✅ Función nueva
        try:
            subprocess.Popen(["virt-viewer", vm_name])
        except FileNotFoundError:
            messagebox.showerror("Error", "virt-viewer no está instalado en el sistema.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir la pantalla de la VM:\n{e}")

    def vm_action(self, action):
        selection = self.vm_listbox.curselection()
        if not selection:
            messagebox.showwarning("Atención", "Debe seleccionar una VM primero.")
            return
        line = self.vm_listbox.get(selection[0])
        vm_name = line.split(" [")[0]
        try:
            domain = self.conn.lookupByName(vm_name)
            if action == "Iniciar":
                if domain.isActive():
                    messagebox.showinfo("Info", f"La VM '{vm_name}' ya está en ejecución.")
                else:
                    domain.create()
                    messagebox.showinfo("Éxito", f"VM '{vm_name}' iniciada correctamente.")
            elif action == "Detener":
                if not domain.isActive():
                    messagebox.showinfo("Info", f"La VM '{vm_name}' ya está detenida.")
                else:
                    domain.destroy()
                    messagebox.showinfo("Éxito", f"VM '{vm_name}' detenida correctamente.")
            elif action == "Reiniciar":
                if domain.isActive():
                    domain.reboot(flags=0)
                    messagebox.showinfo("Éxito", f"VM '{vm_name}' reiniciada.")
                else:
                    messagebox.showinfo("Info", f"No se puede reiniciar: la VM está apagada.")
            elif action == "Eliminar":
                confirm = messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar la VM '{vm_name}'?")
                if confirm:
                    xml = domain.XMLDesc()
                    root = ET.fromstring(xml)
                    disk_paths = []
                    for disk in root.findall(".//disk"):
                        source = disk.find("source")
                        if source is not None and "file" in source.attrib:
                            disk_paths.append(source.attrib["file"])
                    if domain.isActive():
                        domain.destroy()
                    domain.undefine()
                    for path in disk_paths:
                        if os.path.exists(path):
                            os.remove(path)
                    messagebox.showinfo("Éxito", f"VM '{vm_name}' eliminada por completo.")
            elif action == "Ver Pantalla":
                if domain.isActive():
                    threading.Thread(target=self.abrir_virt_viewer, args=(vm_name,), daemon=True).start()
                else:
                    messagebox.showinfo("Info", f"La VM '{vm_name}' debe estar encendida para ver su pantalla.")
            self.load_vms()
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"Ocurrió un error al ejecutar '{action}':\n{e}")

    def create_vm_dialog(self):
        CrearVMDialog(self)

    def show_about(self):
        messagebox.showinfo("Acerca de", "Cliente de Virtualización\nDesarrollado para SO2 - 2025")

class CrearVMDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Crear nueva VM")
        self.geometry("400x400")
        self.master = master

        tk.Label(self, text="Nombre de la VM:").pack(anchor="w", padx=10, pady=5)
        self.name_entry = tk.Entry(self)
        self.name_entry.pack(fill=tk.X, padx=10)

        tk.Label(self, text="RAM (MB):").pack(anchor="w", padx=10, pady=5)
        self.ram_entry = tk.Entry(self)
        self.ram_entry.insert(0, "2048")
        self.ram_entry.pack(fill=tk.X, padx=10)

        tk.Label(self, text="CPUs:").pack(anchor="w", padx=10, pady=5)
        self.cpu_entry = tk.Entry(self)
        self.cpu_entry.insert(0, "2")
        self.cpu_entry.pack(fill=tk.X, padx=10)

        tk.Label(self, text="Sistema Operativo (base):").pack(anchor="w", padx=10, pady=5)
        self.osinfo_var = tk.StringVar()
        self.osinfo_combobox = ttk.Combobox(self, textvariable=self.osinfo_var, state="readonly")
        self.osinfo_options = {
            "Ubuntu 22.04": "ubuntu22.04",
            "Debian 12": "debian12",
            "Linux Mint (basado en Ubuntu)": "ubuntu22.04",
            "Linux genérico 2022": "linux2022",
            "CentOS 9": "centosstream9"
        }
        self.osinfo_combobox['values'] = list(self.osinfo_options.keys())
        self.osinfo_combobox.current(0)
        self.osinfo_combobox.pack(fill=tk.X, padx=10)

        tk.Label(self, text="Archivo ISO:").pack(anchor="w", padx=10, pady=5)
        iso_frame = tk.Frame(self)
        iso_frame.pack(fill=tk.X, padx=10)

        self.iso_entry = tk.Entry(iso_frame)
        self.iso_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_button = tk.Button(iso_frame, text="📁", command=self.browse_iso)
        browse_button.pack(side=tk.RIGHT)

        tk.Button(self, text="Crear VM", command=self.crear_vm).pack(pady=15)

    def browse_iso(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo ISO",
            filetypes=[("Archivos ISO", "*.iso")],
            initialdir=os.path.expanduser("~")
        )
        if file_path:
            self.iso_entry.delete(0, tk.END)
            self.iso_entry.insert(0, file_path)

    def crear_vm(self):
        name = self.name_entry.get().strip()
        ram = self.ram_entry.get().strip()
        cpus = self.cpu_entry.get().strip()
        iso_path = self.iso_entry.get().strip()
        osinfo_value = self.osinfo_options.get(self.osinfo_var.get(), "linux2022")
        disk_path = f"/var/lib/libvirt/images/{name}.qcow2"

        if not all([name, ram, cpus, iso_path]):
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        if not os.path.isfile(iso_path):
            messagebox.showerror("Error", f"No se encontró el archivo ISO en:\n{iso_path}")
            return

        try:
            subprocess.run(["qemu-img", "create", "-f", "qcow2", disk_path, "10G"], check=True)
            subprocess.run([
                "virt-install",
                "--name", name,
                "--ram", ram,
                "--vcpus", cpus,
                "--disk", f"path={disk_path},format=qcow2",
                "--cdrom", iso_path,
                "--osinfo", f"detect=on,name={osinfo_value}",
                "--graphics", "spice",
                "--network", "network=default",
                "--noautoconsole"
            ], check=True)

            messagebox.showinfo("Éxito", f"Máquina virtual '{name}' creada.")
            self.master.load_vms()
            
            # Verificación adicional de soporte gráfico
            try:
                domain = self.master.conn.lookupByName(name)
                xml = domain.XMLDesc()
                root = ET.fromstring(xml)
                graphics = root.find(".//graphics")
                if graphics is not None and graphics.attrib.get("type") not in ("spice", "vnc"):
                    messagebox.showwarning("Advertencia", f"La VM '{name}' no tiene visor gráfico compatible (spice/vnc).")
            except Exception as e:
                print(f"Advertencia: no se pudo verificar soporte gráfico: {e}")

            self.destroy()

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Falló la creación de la VM:\n{e}")

if __name__ == "__main__":
    app = VirtualizationClient()
    app.mainloop()
