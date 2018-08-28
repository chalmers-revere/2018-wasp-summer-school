
controllerParams={}

const controlReq = (track, boxDimensions) => {

	var PedalPosReq=0
	var steeringReq=0
	var boxArea=boxDimensions[0]*boxDimensions[1]

	if (controllerParams.initialBoxArea) {
		controllerParams.Psteer=0.3
		controllerParams.Ppedal=0.3
		controllerParams.Dpedal=0
		
		let dist=(controllerParams.initialBoxArea/boxArea)-1
		let PedalPosReqPpart=controllerParams.Ppedal*dist

		let derivative=(dist-controllerParams.prevDist)/ds
		controllerParams.prevDist=dist
		let PedalPosReqDpart=controllerParams.Dpedal*derivative

		PedalPosReq=PedalPosReqPpart+PedalPosReqDpart

		let normalizeDistToCenter=2*(track[1]-(controllerParams.sizeOfImage[1]/2))/controllerParams.sizeOfImage[1]
		steeringReq=sign(PedalPosReq)*controllerParams.Psteer*normalizeDistToCenter
		
	} else {
		controllerParams.initialBoxArea=boxArea
		controllerParams.prevDist=0
		controllerParams.sizeOfImage=[640,480]
	/*	controllerParams.Psteer=0.3
		controllerParams.Ppedal=0.3
		controllerParams.Dpedal=0 */
		controllerParams.ds=0.1
	}

	return [PedalPosReq,steeringReq]
}