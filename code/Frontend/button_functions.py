import json
import base64
import tempfile
import numpy as np
import requests
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QTableWidgetItem
from vtk.util.numpy_support import vtk_to_numpy
import vtk
import numpy
from stl import mesh
from patient_list import PatientListWindow
from commonHelper import RenderHelper  # Ensure this is properly imported

def load_stl(self):
    # file_path = QFileDialog.getOpenFileName(self, "Select STL file", "", "STL Files (*.stl)")[0]
    # if file_path:
    #     with open(file_path, "rb") as file:
    #             # Encode the file content in base64
    #             self.files_data = base64.b64encode(file.read()).decode('utf-8')
    try:
        if self.fileType == "Upper Arch Segment":
            base64_stl_data = self.file_data['prep_file']
        elif self.fileType == "Lower Arch Segment":
            base64_stl_data = self.file_data['opposing_file']
        elif self.fileType == "Buccal Segment":
            base64_stl_data = self.file_data['buccal_file']
    except Exception as e:
        QMessageBox.warning(self, "Warning", "No file data to load. Register the patient!")
        return

    decoded_stl_data = base64.b64decode(base64_stl_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".stl") as temp_file:
        self.markers.clear()  # Clear the list of markers
        self.points.clear()  # Clear the list of points
        
        temp_file.write(decoded_stl_data)
        temp_file_path = temp_file.name

        reader = vtk.vtkSTLReader()
        reader.SetFileName(temp_file_path)
        reader.Update()

        your_mesh = mesh.Mesh.from_file(temp_file_path)

        self.renderer.RemoveAllViewProps()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()

        self.center = np.mean(vtk_to_numpy(reader.GetOutput().GetPoints().GetData()), axis=0)

        points = np.vstack(np.array([your_mesh.v0, your_mesh.v1, your_mesh.v2]))
        means = np.mean(points, axis=0)
        centered_points = points - means
        covariance_matrix = np.cov(centered_points, rowvar=False)
        eigenvalues, eigenvectors = np.linalg.eig(covariance_matrix)

        sorted_indexes = np.argsort(eigenvalues)[::-1]
        principal_eigenvectors = eigenvectors[:, sorted_indexes]
        top_principal_eigenvectors = principal_eigenvectors[:, :3]
        eigenvectors = top_principal_eigenvectors
        eigenvalues = eigenvalues[sorted_indexes[:3]]

        colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]

        for i, vec in enumerate(eigenvectors.T):
            lineSource = vtk.vtkLineSource()
            lineSource.SetPoint1(self.center)
            lineSource.SetPoint2(self.center + vec * 10)

            lineMapper = vtk.vtkPolyDataMapper()
            lineMapper.SetInputConnection(lineSource.GetOutputPort())

            lineActor = vtk.vtkActor()
            lineActor.SetMapper(lineMapper)
            lineActor.GetProperty().SetColor(colors[i])
            lineActor.GetProperty().SetLineWidth(2)

            self.renderer.AddActor(lineActor)
        
        # Initialize text actor here and store as a class attribute
        self.text_actor = vtk.vtkTextActor()
        self.text_actor.GetTextProperty().SetColor(0, 1, 0)  # Green color
        self.text_actor.GetTextProperty().SetFontSize(20)
        self.text_actor.SetPosition(20, 30)
        self.renderer.AddActor(self.text_actor)

        self.update_disclaimer_text(self.fileType)  # Initial text update

        self.interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        style = RenderHelper(self.renderer, self.center, self.vtkWidget.GetRenderWindow(), self.markers, self.points)
        self.interactor.SetInteractorStyle(style)
        self.interactor.Initialize()
        self.vtkWidget.GetRenderWindow().Render()

def save_to_json(self):
    if not self.points:
        QMessageBox.warning(self, "Warning", "No Data To Save.")
        print("No points to save.")
        return

    json_data = {
        "measurement_type": self.measurement,
        "points": [{"point_name": point["name"], "coordinates": (point["x"], point["y"], point["z"])} for point in self.points]
    }
    file_path = QFileDialog.getSaveFileName(self, "Save File", "", "JSON Files (*.json)")[0]
    if file_path:
        with open(file_path, 'w') as outfile:
            json.dump(json_data, outfile, indent=4)
        print("Data saved to", file_path)

def undo_marker(self):
    if self.markers:
        last_marker = self.markers.pop()
        self.points.pop()
        if 'actor' in last_marker:
            self.renderer.RemoveActor(last_marker['actor'])
        if 'textActor' in last_marker:
            self.renderer.RemoveActor(last_marker['textActor'])
        self.vtkWidget.GetRenderWindow().Render()
        print("Last marker has been undone.")

def reset_markers(self):
    while self.markers:
        marker = self.markers.pop()
        self.points.pop()
        if 'actor' in marker:
            self.renderer.RemoveActor(marker['actor'])
        if 'textActor' in marker:
            self.renderer.RemoveActor(marker['textActor'])
    self.vtkWidget.GetRenderWindow().Render()
    print("All markers have been reset.")

def save_data(self):
    try:
        # url = 'http://3.6.62.207:8080/api/point/list'
        url = 'http://localhost:8080/api/point/list'
        data = {
            "patient_id" : self.file_data['patient_id'],
            "file_type" : self.fileType,
            "measurement_type": self.measurement,
            "points": [{"point_name": point["name"], "coordinates": f"{point['x']},{point['y']},{point['z']}"} for point in self.points]
        }

        print(data["patient_id"])
    
        response = requests.post(url, json=data)
        if response.status_code == 201:
            QMessageBox.information(self, "Success", "The data was saved successfully!")

            # Clear markers and points after successful data transmission
            self.markers.clear()  # Clear the list of markers
            self.points.clear()  # Clear the list of points
            self.renderer.RemoveAllViewProps()  # Optionally remove all actors from the renderer
            self.vtkWidget.GetRenderWindow().Render()  # Re-render the window to update the scene
        else:
            QMessageBox.warning(self, "Error", "Failed to save data.")
            print(response.text, "\n", response)
    except Exception as e:
        QMessageBox.critical(self, "Error", "An error occurred: " + str(e))

def load_points(self):
    try:
        if not hasattr(self, 'file_data') or 'patient_id' not in self.file_data:
            QMessageBox.warning(self, "Warning", "No patient data available. Register a patient first!")
            return

        if not hasattr(self, 'renderer') or self.renderer.GetActors().GetNumberOfItems() == 0:
            QMessageBox.warning(self, "Warning", "No STL file loaded. Load an STL file first!")
            return

        url = f'http://localhost:8080/api/point?patient_id={self.file_data["patient_id"]}'
        print(f"Requesting points from: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            points_data = response.json()
            print(f"Received points data: {points_data}")
            file_type_points = points_data.get(self.fileType, [])
            
            if not file_type_points:
                QMessageBox.information(self, "Info", f"No points found for {self.fileType}.")
                return

            self.markers.clear()
            self.points.clear()

            for point in file_type_points:
                coords = [float(x) for x in point['coordinates'].split(',')]
                position = (coords[0], coords[1], coords[2])
                label = point['pointName']

                sphereSource = vtk.vtkSphereSource()
                sphereSource.SetCenter(position)
                sphereSource.SetRadius(0.1)
                sphereSource.Update()

                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(sphereSource.GetOutputPort())

                sphereActor = vtk.vtkActor()
                sphereActor.SetMapper(mapper)
                sphereActor.GetProperty().SetColor(1, 0, 0)

                textActor = vtk.vtkBillboardTextActor3D()
                textActor.SetInput(label)
                textProp = textActor.GetTextProperty()
                textProp.SetFontSize(18)
                textProp.SetColor(0, 1, 0)
                textProp.SetBold(True)
                textActor.SetPosition(position)

                self.renderer.AddActor(sphereActor)
                self.renderer.AddActor(textActor)

                self.markers.append({
                    "name": label,
                    "x": coords[0],
                    "y": coords[1],
                    "z": coords[2],
                    "actor": sphereActor,
                    "textActor": textActor
                })

                self.points.append({
                    "name": label,
                    "x": coords[0],
                    "y": coords[1],
                    "z": coords[2]
                })

            self.vtkWidget.GetRenderWindow().Render()
            QMessageBox.information(self, "Success", "Points loaded successfully!")
        else:
            QMessageBox.warning(self, "Error", f"Failed to load points: {response.text}")
            print(f"Error response: {response.text}, Status: {response.status_code}")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        print(f"Exception: {str(e)}")


def get_patient_list(self):
    self.patient_list_window = PatientListWindow()
    self.patient_list_window.show()
    response = requests.get("http://localhost:8080/api/patient/patients")
    patients = response.json()
    self.patient_list_window.patient_table.setRowCount(len(patients))
    for i, patient in enumerate(patients):
        self.patient_list_window.patient_table.setItem(i, 0, QTableWidgetItem(str(patient["patient_id"])))
        self.patient_list_window.patient_table.setItem(i, 1, QTableWidgetItem(patient["name"]))
        self.patient_list_window.patient_table.setItem(i, 2, QTableWidgetItem(str(patient["pre_PAR_score"])))
        self.patient_list_window.patient_table.setItem(i, 3, QTableWidgetItem(str(patient["post_PAR_score"])))


def view_points(self):
    selected_row = self.patient_table.currentRow()
    patient_id = self.patient_table.item(selected_row, 0).text()
    response = requests.get(f"http://localhost:8080/api/patients/{patient_id}/points")
    points = response.json()
    # Display points in a new window or on a map