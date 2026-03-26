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

  csv_submitted = false;
  returned_csv: string = "";
  public file: File | null = null;
  question: string = "";
  model_output: string = "";

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
      this.returned_csv = results.file;
    });

    console.log(this.returned_csv);
    this.csv_submitted = true;
  }

  onStream() {
    this._modelService.updateQuestion(this.question).subscribe((results: any) => {
      console.log(results.info)
    });

    
    this._modelService.getStream().subscribe((event: any) => {
      if (event.type === HttpEventType.DownloadProgress) {
        // Partial text data arrives here
        
        this.model_output = event.partialText;
        console.log(this.model_output);
        this._changeDetectorRef.detectChanges();
      }
    });
  }
}
