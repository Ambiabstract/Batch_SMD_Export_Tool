import pymxs
import os

rt = pymxs.runtime

# Глобальная переменная для хранения экземпляра экспортера
exporter_instance = None

g_script_description = f"Ambiabstract batch SMD Export Tool"
g_script_link = f"https://github.com/Ambiabstract"
g_script_version = f"0.0.2"

class SMDExporter:
    def __init__(self):
        self.create_ui()

    def create_ui(self):
        global g_script_description
        global g_script_version

        # Создание окна
        self.dialog = rt.newRolloutFloater(f"{g_script_description} v.{g_script_version}", 400, 150)

        # Создание Rollout через MaxScript
        rollout_code = '''
        rollout smdExportRollout "Ambiabstract batch SMD Export Tool" width:400 height:150 (
            label descLabel "Plese select objects you want to export as SMDs." pos:[10,5]
            label descLabel2 "Then please pick an export folder path." pos:[10,20]
            editText pathEdit "" pos:[10,40] width:300
            button browseBtn "Browse" pos:[320,40] width:60
            checkBox placeholderCheckbox "Placeholder Checkbox (useless for now)" pos:[10,70]
            button exportBtn "Start Export" pos:[10,100] width:370

            on browseBtn pressed do (
                local folder = getSavePath caption:"Select Folder"
                if folder != undefined do pathEdit.text = folder
            )

            on exportBtn pressed do (
                local correctedPath = substituteString pathEdit.text "\\\\" "/"
                python.execute("exporter_instance.export_smd('" + correctedPath + "')")
            )
        )
        '''

        rt.execute(rollout_code)
        rt.addRollout(rt.smdExportRollout, self.dialog)

    def export_smd(self, output_dir):
        if not output_dir or not os.path.isdir(output_dir):
            rt.messageBox("Please select a valid output directory.", title="Error")
            return

        selected_objs = rt.selection
        if not selected_objs:
            rt.messageBox("No objects selected.", title="Error")
            return

        for obj in selected_objs:
            self.export_object_to_smd(obj, output_dir)

        rt.messageBox("SMD Export Completed.", title="Success")

    def export_object_to_smd(self, obj, output_dir):
        global g_script_description
        global g_script_link
        global g_script_version

        # Проверка и конвертация объекта в Editable Poly
        if not rt.isKindOf(obj, rt.Editable_Poly):
            obj = rt.convertTo(obj, rt.Editable_Poly)

        filename = f"{obj.name}.smd"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as smd_file:
            smd_file.write(f"// SMD file generated by {g_script_description} v.{g_script_version}\n")
            smd_file.write(f"// {g_script_link}\n")
            smd_file.write("version 1\n")
            smd_file.write("nodes\n")
            smd_file.write(f"0 \"{obj.name}\" -1\n")
            smd_file.write("end\n")

            smd_file.write("skeleton\n")
            smd_file.write("time 0\n")
            smd_file.write("0 0 0 0 0 0 -1.5708\n")
            smd_file.write("end\n")

            smd_file.write("triangles\n")

            face_count = rt.polyOp.getNumFaces(obj)
            for i in range(1, face_count + 1):
                verts = rt.polyOp.getFaceVerts(obj, i)
                material_name = obj.material.name if obj.material else "default_material"

                for j in range(1, len(verts) - 1):
                    indices = [verts[0], verts[j], verts[j+1]]

                    smd_file.write(f"{material_name}\n")
                    for idx in indices:
                        vert = rt.polyOp.getVert(obj, idx)
                        norm = rt.polyOp.getFaceNormal(obj, i)
                        uv = rt.polyOp.getMapVert(obj, 1, idx) if rt.polyOp.getNumMaps(obj) > 0 else rt.Point2(0, 0)

                        smd_file.write(f"0 {vert.x} {vert.y} {vert.z} {norm.x} {norm.y} {norm.z} {uv.x} {uv.y}\n")

            smd_file.write("end\n")

# Запуск экспортера
exporter_instance = SMDExporter()
