import { Component, signal, OnInit, ChangeDetectorRef } from '@angular/core';
import { NgForm, FormsModule } from '@angular/forms';
import { HttpEventType } from '@angular/common/http';
import { RouterOutlet } from '@angular/router';
import { ModelService } from './services/services';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('angular_website');

  csv_submitted: boolean = false;
  returned_csv: string = "";
  public file: File | null = null;
  question: string = "";
  model_output: string = "";

  file_upload_failure:string = "File failed to upload.";

  constructor(private _modelService:ModelService, private _changeDetectorRef:ChangeDetectorRef) {}

  ngOnInit() {
    this._modelService.getTest().subscribe((results: any) => {
      console.log(results.info);
    })
  }

  onFileSelected(event: any) {
    this.file = event.target.files[0];
  }

  onQuestionGiven(value: string){
    this.question = value;
  }

  onSubmit(){ 
    if(!this.file){
      return;
    }

    const formData = new FormData();
    formData.append('file', this.file, this.file.name);



    this._modelService.postCSV(formData).subscribe((results: any) => {
      if (results.status == 200){
        this.returned_csv = results.info;
      }
      else {
        console.log(results.info)
        this.returned_csv = this.file_upload_failure;
      }
      this._changeDetectorRef.detectChanges();
    });

    console.log(this.returned_csv);
    if (this.returned_csv !== "" && this.returned_csv !== this.file_upload_failure){
      this.csv_submitted = true;
      this._changeDetectorRef.markForCheck();
      this._changeDetectorRef.detectChanges();
    }
    
  }

  onStream() {
    this._modelService.updateQuestion(this.question).subscribe((results: any) => {
      console.log(results.info)
    });

    
    this._modelService.getAgentStream().subscribe((event: any) => {
      if (event.type === HttpEventType.DownloadProgress) {
        this.model_output = event.partialText;
        this._changeDetectorRef.markForCheck();
        this._changeDetectorRef.detectChanges();
        console.log(this.model_output);
      }
    });
  }
}
