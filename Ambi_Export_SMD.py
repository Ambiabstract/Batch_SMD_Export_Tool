import pymxs
import os

rt = pymxs.runtime

# Глобальная переменная для хранения экземпляра экспортера
exporter_instance = None

# Информация о скрипте
g_script_description = f"Ambiabstract batch SMD Export Tool"
g_script_link = f"https://github.com/Ambiabstract"
g_script_version = f"0.2.0"

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
            label descLabel "Please select objects you want to export as SMDs." pos:[10,5]
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
                local rawPath = pathEdit.text
                /*
                Instead of manually substituting slashes, we rely on Python's os.path.normpath.
                This reduces issues with spaces or special characters in paths, especially on Windows.
                */
                python.execute("import os\ncorrected_path = os.path.normpath(r'" + rawPath + "')\nexporter_instance.export_smd(corrected_path)")
            )
        )
        '''

        rt.execute(rollout_code)
        rt.addRollout(rt.smdExportRollout, self.dialog)

    def export_smd(self, output_dir):
        """
        Запускает экспорт для всех выделенных объектов в заданную папку.
        Проверяет, что путь корректный и что выделены какие-то объекты.
        """
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

    def get_vertex_normals(self, obj):
        """
        Получает нормали вершин объекта:
        1. Создаёт snapshot копию исходного объекта.
        2. Если нужно, конвертирует её в Editable Poly.
        3. Накладывает Edit_Normals модификатор.
        4. Считывает нормали.
        5. Удаляет временный объект.
        Возвращает словарь ( (vert_idx, smooth_group) -> Point3 ), усреднённые нормали.
        """
        temp_obj = rt.snapshot(obj)

        # Если копия не Editable_Poly, конвертируем.
        if not rt.isKindOf(temp_obj, rt.Editable_Poly):
            temp_obj = rt.convertTo(temp_obj, rt.Editable_Poly)

        edit_normals_mod = rt.Edit_Normals()
        rt.addModifier(temp_obj, edit_normals_mod)
        rt.modPanel.setCurrentObject(edit_normals_mod)

        # Инвертированная матрица для трансформации в space исходного объекта.
        obj_tm_inverse = rt.inverse(obj.transform)
        num_faces = rt.polyOp.getNumFaces(temp_obj)
        vertex_normals = {}
        smooth_groups = {}

        for i in range(1, num_faces + 1):
            face_verts = rt.polyOp.getFaceVerts(temp_obj, i)
            smooth_group = rt.polyOp.getFaceSmoothGroup(temp_obj, i)

            for j, vert_idx in enumerate(face_verts):
                normal_id = rt.EditNormals.GetNormalID(edit_normals_mod, i, j + 1)
                if normal_id != 0:
                    normal_ws = rt.EditNormals.GetNormal(edit_normals_mod, normal_id)
                    # Преобразуем нормаль из world space temp_obj обратно в space исходного объекта.
                    normal_os = normal_ws * obj_tm_inverse.rotation

                    key = (vert_idx, smooth_group)
                    if key not in vertex_normals:
                        vertex_normals[key] = rt.Point3(0, 0, 0)
                        smooth_groups[key] = 0

                    vertex_normals[key] += normal_os
                    smooth_groups[key] += 1

        # Удаляем временный объект, чтобы не затронуть исходный стек.
        rt.delete(temp_obj)

        # Усредняем нормали.
        for key in vertex_normals:
            vertex_normals[key] /= smooth_groups[key]
            vertex_normals[key] = rt.normalize(vertex_normals[key])

        return vertex_normals

    def export_object_to_smd(self, obj, output_dir):
        """
        Экспортирует отдельный объект в SMD.
        Если объект не Editable Poly, вместо конвертации добавляем Edit_Poly поверх стека.
        """
        global g_script_description
        global g_script_link
        global g_script_version

        # Если объект не Editable Poly, добавляем Edit_Poly
        if not rt.isKindOf(obj, rt.Editable_Poly):
            edit_poly_mod = rt.Edit_Poly()
            rt.addModifier(obj, edit_poly_mod)
            # Убедимся, что polyOp будет работать с вершинами/фейсами поверх нового модификатора.
            rt.modPanel.setCurrentObject(edit_poly_mod)

        filename = f"{obj.name}.smd"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, 'w') as smd_file:
                # Header lines
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

                # Получаем нормали
                vertex_normals = self.get_vertex_normals(obj)
                face_count = rt.polyOp.getNumFaces(obj)

                # Проходим по всем фейсам
                for i in range(1, face_count + 1):
                    verts = rt.polyOp.getFaceVerts(obj, i)
                    map_faces = []

                    # Если у объекта есть UV-координаты
                    if rt.polyOp.getNumMapVerts(obj, 1) > 0:
                        try:
                            map_faces = rt.polyOp.getMapFace(obj, 1, i)
                        except:
                            map_faces = []

                    # Если map_faces меньше количества вершин, заполним недостающие индексы нулями.
                    if len(map_faces) < len(verts):
                        map_faces += [0]*(len(verts)-len(map_faces))

                    smooth_group = rt.polyOp.getFaceSmoothGroup(obj, i)
                    face_mat_id = rt.polyOp.getFaceMatID(obj, i)

                    # Преобразуем 1-based ID -> 0-based индекс
                    actual_sub_index = face_mat_id - 1

                    # Работаем с мульти-саб материалом, если он есть
                    if (
                        obj.material 
                        and rt.isKindOf(obj.material, rt.MultiSubMaterial)
                        and actual_sub_index >= 0
                        and actual_sub_index < obj.material.numsubs
                    ):
                        sub_mat = obj.material[actual_sub_index]
                        if sub_mat and sub_mat.name:
                            material_name = sub_mat.name
                        else:
                            material_name = "default_material"
                    else:
                        # Иначе используем название материала самого объекта (или default)
                        material_name = (
                            obj.material.name 
                            if (obj.material and hasattr(obj.material, 'name'))
                            else "default_material"
                        )

                    # Триангулируем фейс (fan из verts[0])
                    for j in range(1, len(verts) - 1):
                        if j >= len(map_faces) or (j + 1) >= len(map_faces):
                            # Недостаточно UV-данных для треугольника, пропускаем.
                            continue

                        indices = [verts[0], verts[j], verts[j+1]]
                        uv_indices = [map_faces[0], map_faces[j], map_faces[j+1]]

                        smd_file.write(f"{material_name}\n")

                        # Записываем поочередно три вершины
                        for idx, uv_idx in zip(indices, uv_indices):
                            vert = rt.polyOp.getVert(obj, idx)
                            norm = vertex_normals.get((idx, smooth_group), rt.Point3(0, 0, 0))

                            # Смотрим, есть ли для этой вершины корректный UV
                            if rt.polyOp.getNumMapVerts(obj, 1) > 0 and uv_idx <= rt.polyOp.getNumMapVerts(obj, 1):
                                uv = rt.polyOp.getMapVert(obj, 1, uv_idx)
                            else:
                                uv = rt.Point2(0, 0)

                            smd_file.write(
                                f"0 {vert.x} {vert.y} {vert.z} "
                                f"{norm.x} {norm.y} {norm.z} "
                                f"{uv.x} {uv.y}\n"
                            )

                smd_file.write("end\n")
        except IOError:
            rt.messageBox(f"Failed to write file: {filepath}", title="Error")

# Запуск экспортера
exporter_instance = SMDExporter()
