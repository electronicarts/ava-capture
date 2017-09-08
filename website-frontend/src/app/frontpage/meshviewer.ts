//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, ElementRef } from '@angular/core';

import * as THREE from 'three';
var OrbitControls = require('three-orbit-controls')(THREE);
var OBJLoader = require('three-obj-loader')(THREE);

@Component({
  selector: 'meshviewer',
  template: '<div style="display:inline-block;"></div>'
})
export class MeshViewerComponent {

    @Input() mesh_file : string;
    @Input() diffuse_file : string;
    @Input() normals_file : string;
    @Input('width') canvas_width : number;
    @Input('height') canvas_height : number;

    el: ElementRef;

    scene = null;
    renderer = null;
    camera = null;
    cameraTarget = null;
    controls = null;

    constructor(el: ElementRef) {
      this.el = el;
    }

    addShadowedLight(x, y, z, color, intensity) {
      const directionalLight = new THREE.DirectionalLight(color, intensity);
      directionalLight.position.set(x, y, z);
      this.scene.add(directionalLight);
      const d = 1;
      directionalLight.shadow.camera.left = -d;
      directionalLight.shadow.camera.right = d;
      directionalLight.shadow.camera.top = d;
      directionalLight.shadow.camera.bottom = -d;
      directionalLight.shadow.camera.near = 1;
      directionalLight.shadow.camera.far = 4;
      directionalLight.shadow.mapSize.width = 1024;
      directionalLight.shadow.mapSize.height = 1024;
      directionalLight.shadow.bias = -0.005;
    }

    init() {

      var objLoader = new THREE.OBJLoader();
      objLoader.load( this.mesh_file, object => {

        // Center camera to the mesh's bounding box
        var bbox = new THREE.Box3().setFromObject(object);
        this.cameraTarget = bbox.getCenter();

        // Create material for the mesh
        var phong = new THREE.MeshPhongMaterial({color: 0xFFFFFF, specular: 0x101010});
        object.traverse( child => {
          if ( child instanceof THREE.Mesh ) {
            child.material = phong;
          }
        } );

        var textureLoader = new THREE.TextureLoader();

        // Load diffuse map
        if (this.diffuse_file) {
          textureLoader.load( this.diffuse_file, tex => {
            phong.map = tex;
            phong.needsUpdate = true;
            this.render();
          });
        }

        // Load normal map
        if (this.normals_file) {
          textureLoader.load( this.normals_file, tex => {
            phong.normalMap = tex;
            phong.needsUpdate = true;
            this.render();
          });
        }

        // Ad dobject to scene
        this.scene.add( object );
        this.render();
      } );

      // Scene
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0x72645b, 300, 400);

      // Camera
      this.camera = new THREE.PerspectiveCamera(15, this.canvas_width / this.canvas_height, 1, 400);
      this.camera.position.set(0, 10, 100);
      this.cameraTarget = new THREE.Vector3(0, 0, 0);

      // Lights
      this.scene.add(new THREE.HemisphereLight(0x443333, 0x111122));
      this.addShadowedLight(1, 1, 1, 0xffffff, 1.35);
      this.addShadowedLight(0.5, 1, -1, 0xffaa00, 1);

      // Renderer
      this.renderer = new THREE.WebGLRenderer({antialias: true});
      this.renderer.setClearColor(this.scene.fog.color);
      this.renderer.setPixelRatio(window.devicePixelRatio);
      this.renderer.gammaInput = true;
      this.renderer.gammaOutput = true;
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.renderReverseSided = false;
      this.renderer.setSize(this.canvas_width, this.canvas_height);

      // Camera controls
      this.controls = new OrbitControls( this.camera, this.renderer.domElement );
      this.controls.addEventListener( 'change', () => this.render() );
      
      this.el.nativeElement.appendChild(this.renderer.domElement);
    }

    render() {
      this.renderer.render(this.scene, this.camera);
    }

    onWindowResize(event) {
      //   this.camera.aspect = event.target.innerWidth / event.target.innerHeight;
      //   this.camera.updateProjectionMatrix();
      //   this.renderer.setSize(event.target.innerWidth, event.target.innerHeight);      
    }

    ngOnInit(): void {
      this.init();
      this.render();
    }

}
