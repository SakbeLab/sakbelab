# OVA de SakbeLab: Debian 13 mínimo + SakbeLab, construida de forma reproducible.
#
#   packer init .
#   packer build .
#
# Resultado: output/sakbelab-<versión>.ova (VirtualBox; se importa también en VMware).

packer {
  required_plugins {
    virtualbox = {
      version = ">= 1.1.1"
      source  = "github.com/hashicorp/virtualbox"
    }
  }
}

variable "version" {
  type    = string
  default = "0.1.0"
}

variable "branch" {
  type        = string
  default     = "main"
  description = "Rama de GitHub que se instala dentro de la OVA."
}

variable "debian_version" {
  type        = string
  default     = "13.6.0"
  description = "Versión del ISO netinst de Debian 13. Si ya no es la vigente, usá la URL de archive."
}

variable "debian_dir" {
  type    = string
  default = "https://cdimage.debian.org/cdimage/release"
}

locals {
  iso_dir = "${var.debian_dir}/${var.debian_version}/amd64/iso-cd"
}

source "virtualbox-iso" "sakbelab" {
  vm_name              = "SakbeLab-${var.version}"
  guest_os_type        = "Debian_64"
  iso_url              = "${local.iso_dir}/debian-${var.debian_version}-amd64-netinst.iso"
  iso_checksum         = "file:${local.iso_dir}/SHA256SUMS"
  disk_size            = 40960
  hard_drive_interface = "sata"
  memory               = 4096
  cpus                 = 2
  headless             = true
  http_directory       = "http"
  boot_wait            = "5s"
  boot_command = [
    "<esc><wait>",
    "install auto=true priority=critical ",
    "url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg ",
    "hostname=sakbelab domain=local ",
    "<enter>"
  ]
  ssh_username     = "root"
  ssh_password     = "sakbe"
  ssh_timeout      = "60m"
  shutdown_command = "shutdown -P now"
  format           = "ova"
  output_directory = "output"
  vboxmanage = [
    ["modifyvm", "{{ .Name }}", "--nested-hw-virt", "on"],
    ["modifyvm", "{{ .Name }}", "--nic1", "nat"],
    ["modifyvm", "{{ .Name }}", "--natpf1", "web,tcp,,8080,,80"],
    ["modifyvm", "{{ .Name }}", "--natpf1", "ssh,tcp,,2222,,22"],
    ["modifyvm", "{{ .Name }}", "--graphicscontroller", "vmsvga"],
    ["modifyvm", "{{ .Name }}", "--audio-enabled", "off"]
  ]
  export_opts = [
    "--manifest",
    "--vsys", "0",
    "--product", "SakbeLab",
    "--version", "${var.version}",
    "--producturl", "https://sakbelab.dev",
    "--description", "Emulador de redes open source. Abrí la dirección que aparece en la consola de la VM."
  ]
}

build {
  sources = ["source.virtualbox-iso.sakbelab"]

  provisioner "file" {
    source      = "../tools/install.sh"
    destination = "/root/install.sh"
  }

  provisioner "shell" {
    inline = ["SAKBE_BRANCH=${var.branch} bash /root/install.sh"]
  }

  provisioner "shell" {
    script = "scripts/finalize.sh"
  }

  post-processor "shell-local" {
    inline = ["cd output && mv SakbeLab-${var.version}.ova sakbelab-${var.version}.ova && sha256sum sakbelab-${var.version}.ova > sakbelab-${var.version}.ova.sha256"]
  }
}
